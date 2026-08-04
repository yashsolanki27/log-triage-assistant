"""Live LLM integration tests — calls real OpenAI endpoint.

These tests exercise the actual LLM to catch prompt regressions or API changes.
They are skipped by default; run with: pytest -m live
Requires OPENCODE_API_KEY environment variable.
"""

import json
import os

import pytest

from src.classifier import classify_log, VALID_CATEGORIES
from src.parser import parse_log
from src.prompts import build_classification_prompt


# Skip all tests in this module if OPENCODE_API_KEY is not set
pytestmark = pytest.mark.live


@pytest.fixture(scope="module")
def requires_api_key():
    """Skip test if OPENCODE_API_KEY is not set."""
    api_key = os.environ.get("OPENCODE_API_KEY")
    if not api_key:
        pytest.skip("OPENCODE_API_KEY not set — skipping live LLM test")
    return api_key


@pytest.fixture(scope="module")
def live_client(requires_api_key):
    """Create a real OpenAI client for live tests."""
    import openai
    return openai.OpenAI(
        base_url=os.environ.get("OPENCODE_BASE_URL", "https://opencode.ai/zen/v1"),
        api_key=requires_api_key,
    )


# --- Sample logs for each category ---

LIVE_TEST_CASES = [
    {
        "label": "Java NPE → next-tache-error",
        "raw_log": (
            "2024-03-15 10:23:45 ERROR [order-service] - Processing failed\n"
            "java.lang.NullPointerException: Cannot invoke method getStatus() on null object\n"
            "    at com.example.OrderProcessor.process(OrderProcessor.java:142)\n"
        ),
        "expected_category": "next-tache-error",
    },
    {
        "label": "Masterless order → state-transition-block",
        "raw_log": (
            "WorkflowEngine: state machine halted\n"
            "Masterless order detected: order ORD-456 missing required state transition\n"
            "CollaborationWaitFailure: CRM cannot reach provisioning service for order ORD-111\n"
        ),
        "expected_category": "state-transition-block",
    },
    {
        "label": "DSLAM failure → provisioning-fault",
        "raw_log": (
            "2024-03-15 10:23:45 INFO  DSLAM-Provisioner - Starting node assignment\n"
            "2024-03-15 10:23:46 WARN  DSLAM-Provisioner - OLT port 3/0/12 unavailable\n"
            "2024-03-15 10:23:47 ERROR DSLAM-Provisioner - Failed to assign BNG node for subscriber 88123\n"
        ),
        "expected_category": "provisioning-fault",
    },
    {
        "label": "SOAP fault → api-integration-error",
        "raw_log": (
            "[2024-03-15T10:23:45Z] POST /api/v1/orders 500\n"
            'Payload: {"orderId": "ORD-12345", "action": "activate"}\n'
            'Response: {"error": "SoapFaultException: ISAP returned fault", "code": 500}\n'
        ),
        "expected_category": "api-integration-error",
    },
    {
        "label": "Normal disk usage → unclassified",
        "raw_log": "Disk usage at 45% — within normal operating parameters",
        "expected_category": "unclassified",
    },
]


class TestLiveLLMClassification:
    """Integration tests that call the real LLM endpoint."""

    @pytest.mark.parametrize("case", LIVE_TEST_CASES, ids=[c["label"] for c in LIVE_TEST_CASES])
    def test_classify_live(self, case, live_client):
        """Full pipeline: raw log → parse → classify with real LLM → verify category."""
        parsed = parse_log(case["raw_log"])
        assert parsed["extracted_error_line"], "parser must extract a non-empty error line"

        result = classify_log(parsed, client=live_client)

        # Verify schema
        assert set(result.keys()) == {
            "category",
            "root_cause_summary",
            "confidence",
            "suggested_action",
            "unclassified_reason",
        }
        assert result["category"] in VALID_CATEGORIES
        assert isinstance(result["confidence"], int)
        assert 0 <= result["confidence"] <= 100
        assert result["root_cause_summary"]
        assert result["suggested_action"]

        # If confidence >= 70, category must match expected
        if result["confidence"] >= 70:
            assert result["category"] == case["expected_category"], (
                f"Expected '{case['expected_category']}', got '{result['category']}' "
                f"(confidence={result['confidence']}%)"
            )
        else:
            # Low confidence → forced unclassified
            assert result["category"] == "unclassified"
            assert result["unclassified_reason"]

    def test_prompt_contains_error_line(self, live_client):
        """Verify the error line from parser is included in the LLM prompt."""
        raw_log = (
            "2024-03-15 10:23:45 ERROR OrderCalculationException: PriceEngine threw RuntimeException\n"
        )
        parsed = parse_log(raw_log)
        assert "OrderCalculationException" in parsed["extracted_error_line"]

        result = classify_log(parsed, client=live_client)
        assert result["category"] in VALID_CATEGORIES

    def test_unclassified_reason_populated(self, live_client):
        """Verify unclassified logs get a non-empty reason."""
        raw_log = "System running normally — no errors detected in last 24 hours"
        parsed = parse_log(raw_log)
        result = classify_log(parsed, client=live_client)

        if result["category"] == "unclassified":
            assert result["unclassified_reason"], "unclassified must have a reason"

    def test_confidence_below_threshold_forces_unclassified(self, live_client):
        """Verify that low confidence correctly forces unclassified category."""
        # Normal text that should not match any error category
        raw_log = "User login successful from IP 192.168.1.100 at 14:32:11"
        parsed = parse_log(raw_log)
        result = classify_log(parsed, client=live_client)

        if result["confidence"] < 70:
            assert result["category"] == "unclassified"
            assert "below" in result["unclassified_reason"].lower()


class TestLivePromptEffectiveness:
    """Test that the prompt produces consistent, well-formed responses."""

    def test_prompt_returns_valid_json(self, live_client):
        """Verify LLM returns parseable JSON for a simple log."""
        log_text = "NullPointerException at com.example.Main.run(Main.java:10)"
        prompt = build_classification_prompt(log_text)

        message = live_client.chat.completions.create(
            model=os.environ.get("LLM_MODEL_NAME", "deepseek-v4-flash-free"),
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        raw_response = message.choices[0].message.content

        # Strip JSON fences if present
        text = raw_response.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()

        result = json.loads(text)

        required_keys = {
            "category",
            "root_cause_summary",
            "confidence",
            "suggested_action",
            "unclassified_reason",
        }
        assert required_keys.issubset(result.keys())

    def test_all_categories_classifiable(self, live_client):
        """Verify each category can be triggered by appropriate log text."""
        test_logs = {
            "next-tache-error": "java.lang.ArithmeticException: / by zero in billing calc",
            "state-transition-block": "Masterless order detected: order ORD-456 missing required state transition",
            "provisioning-fault": "DSLAM-Provisioner: Failed to assign BNG node for subscriber 88123",
            "api-integration-error": "SoapFaultException: ISAP returned fault for request activateOrder",
        }

        for expected_cat, log_text in test_logs.items():
            parsed = parse_log(log_text)
            result = classify_log(parsed, client=live_client)

            if result["confidence"] >= 70:
                assert result["category"] == expected_cat, (
                    f"Log '{log_text[:50]}...' should classify as '{expected_cat}', "
                    f"got '{result['category']}'"
                )
