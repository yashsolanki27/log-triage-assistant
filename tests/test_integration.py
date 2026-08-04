"""Integration tests — full parser → classifier pipeline with mocked LLM."""

import json
from unittest.mock import MagicMock

from src.classifier import classify_log
from src.parser import parse_log


def _mock_openai_client(response_payload: dict):
    """Return a mock OpenAI client that yields the given JSON response."""
    mock_message = MagicMock()
    mock_message.content = json.dumps(response_payload)

    mock_choice = MagicMock()
    mock_choice.message = mock_message

    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    client = MagicMock()
    client.chat.completions.create.return_value = mock_response
    return client


# --- Samples: raw log text → expected pipeline output ---

PIPELINE_CASES = [
    {
        "label": "Java NullPointerException → next-tache-error",
        "raw_log": (
            "2024-03-15 10:23:45 ERROR [order-service] - Processing failed\n"
            "java.lang.NullPointerException: Cannot invoke method getStatus() on null object\n"
            "    at com.example.OrderProcessor.process(OrderProcessor.java:142)\n"
        ),
        "mock_category": "next-tache-error",
    },
    {
        "label": "DSLAM provisioning fault",
        "raw_log": (
            "2024-03-15 10:23:45 INFO  DSLAM-Provisioner - Starting node assignment\n"
            "2024-03-15 10:23:46 WARN  DSLAM-Provisioner - OLT port 3/0/12 unavailable\n"
            "2024-03-15 10:23:47 ERROR DSLAM-Provisioner - Failed to assign BNG node for subscriber 88123\n"
        ),
        "mock_category": "provisioning-fault",
    },
    {
        "label": "SOAP API error → api-integration-error",
        "raw_log": (
            "[2024-03-15T10:23:45Z] POST /api/v1/orders 500\n"
            'Payload: {"orderId": "ORD-12345", "action": "activate"}\n'
            'Response: {"error": "SoapFaultException: ISAP returned fault", "code": 500}\n'
        ),
        "mock_category": "api-integration-error",
    },
    {
        "label": "State-transition block",
        "raw_log": (
            "WorkflowEngine: state machine halted\n"
            "Masterless order detected: order ORD-456 missing required state transition\n"
            "CollaborationWaitFailure: CRM cannot reach provisioning service for order ORD-111\n"
        ),
        "mock_category": "state-transition-block",
    },
    {
        "label": "Low-confidence log → forced unclassified",
        "raw_log": "Disk usage at 45% — within normal operating parameters",
        "mock_category": "unclassified",
        "mock_confidence": 30,
    },
]


def test_pipeline_end_to_end():
    """Full pipeline: raw log → parse_log → classify_log → valid result."""
    for case in PIPELINE_CASES:
        # Step 1 — parse
        parsed = parse_log(case["raw_log"])
        assert "extracted_error_line" in parsed
        assert parsed["extracted_error_line"], "parser must extract a non-empty error line"

        # Step 2 — classify (mocked LLM)
        confidence = case.get("mock_confidence", 85)
        payload = {
            "category": case["mock_category"],
            "root_cause_summary": f"Root cause: {case['mock_category']}",
            "confidence": confidence,
            "suggested_action": "Investigate",
            "unclassified_reason": None,
        }
        # low-confidence case gets a reason
        if confidence < 70:
            payload["unclassified_reason"] = f"Confidence {confidence}% below threshold"

        mock_client = _mock_openai_client(payload)
        result = classify_log(parsed, client=mock_client)

        # Assert pipeline output schema
        assert set(result.keys()) == {
            "category",
            "root_cause_summary",
            "confidence",
            "suggested_action",
            "unclassified_reason",
        }
        # Confidence below threshold forces unclassified
        if confidence < 70:
            assert result["category"] == "unclassified"
            assert result["unclassified_reason"] is not None
        else:
            assert result["category"] == case["mock_category"]
        assert 0 <= result["confidence"] <= 100


def test_pipeline_error_line_fed_to_classifier():
    """Verify the extracted_error_line (not raw_text) is what the classifier processes."""
    raw_log = (
        "2024-03-15 10:23:45 INFO  Starting batch\n"
        "2024-03-15 10:23:46 ERROR OrderCalculationException: PriceEngine threw RuntimeException\n"
    )
    parsed = parse_log(raw_log)
    assert "OrderCalculationException" in parsed["extracted_error_line"]

    payload = {
        "category": "next-tache-error",
        "root_cause_summary": "Calculation engine failed",
        "confidence": 90,
        "suggested_action": "Check PriceEngine logs",
        "unclassified_reason": None,
    }
    mock_client = _mock_openai_client(payload)
    result = classify_log(parsed, client=mock_client)

    assert result["category"] == "next-tache-error"
    # Ensure the classifier was called with the prompt containing the extracted error line
    call_args = mock_client.chat.completions.create.call_args
    sent_prompt = call_args.kwargs["messages"][0]["content"]
    assert "OrderCalculationException" in sent_prompt
