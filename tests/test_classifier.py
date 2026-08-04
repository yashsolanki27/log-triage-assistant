"""Tests for src/classifier.py — Unit 3 classifier."""

import json
from unittest.mock import MagicMock

import pytest

from src.classifier import (
    VALID_CATEGORIES,
    CONFIDENCE_THRESHOLD,
    classify_log,
    _validate_input,
    _parse_response,
    _apply_confidence_rule,
    _validate_output,
)


# --- Fixtures ---

def _make_parsed_log(error_line: str) -> dict:
    return {"raw_text": f"raw: {error_line}", "extracted_error_line": error_line}


def _make_llm_response(category: str, confidence: int = 85, reason: str = None) -> str:
    return json.dumps({
        "category": category,
        "root_cause_summary": f"Test summary for {category}",
        "confidence": confidence,
        "suggested_action": "Investigate the issue",
        "unclassified_reason": reason,
    })


def _mock_openai(response_text: str):
    """Return a mock OpenAI client that returns the given response."""
    mock_message = MagicMock()
    mock_message.content = response_text

    mock_choice = MagicMock()
    mock_choice.message = mock_message

    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client


# --- 5 logs per category (5 categories x 5 = 25 cases) ---

CATEGORY_LOGS = {
    "next-tache-error": [
        "NullPointerException at com.example.OrderProcessor.process(OrderProcessor.java:142)",
        "java.lang.ArithmeticException: / by zero in billing calc",
        "CalculationException: NextTache compute failed for order ORD-789",
        "java.lang.IllegalArgumentException: Invalid tax rate in order processing",
        "OrderCalculationException: PriceEngine threw RuntimeException during batch",
    ],
    "state-transition-block": [
        "Masterless order detected: order ORD-456 missing required state transition",
        "CRM-to-OSS handoff stuck: collab-wait timeout for subscriber 99887",
        "StateTransitionBlock: Order stuck in PENDING_ACTIVATION for 48 hours",
        "WorkflowEngine: state machine halted — missing transition from PROVISIONED to ACTIVE",
        "CollaborationWaitFailure: CRM cannot reach provisioning service for order ORD-111",
    ],
    "provisioning-fault": [
        "DSLAM-Provisioner: Failed to assign BNG node for subscriber 88123",
        "OLT port 3/0/12 unavailable — cannot provision VDSL profile",
        "LMG error: node assignment failed for fiber subscriber 55667",
        "ProvisioningFault: DSLAM slot 12 reject — port capacity exceeded",
        "BNG connection timeout for subscriber PPPoE session 44332",
    ],
    "api-integration-error": [
        "SoapFaultException: ISAP returned fault for request activateOrder",
        "REST API error: POST /api/v1/orders returned 400 — Invalid payload structure",
        "OFM interface error: payload mismatch in order activation request",
        "ApiIntegrationError: SOAP envelope malformed at line 23",
        "HTTP 502 Bad Gateway from downstream ISAP service during order sync",
    ],
    "unclassified": [
        "System running normally — no errors detected in last 24 hours",
        "Info: batch job completed successfully with 1500 records processed",
        "Disk usage at 45% — within normal operating parameters",
        "Scheduled maintenance window confirmed for Saturday 02:00-06:00",
        "User login successful from IP 192.168.1.100 at 14:32:11",
    ],
}


# --- Unit 3 test: 5 synthetic logs per category → correct category >=90% ---

def _classify_with_mock(error_line: str, expected_category: str, confidence: int = 85):
    """Helper: mock LLM and classify a log, verify category."""
    response = _make_llm_response(expected_category, confidence)
    mock_client = _mock_openai(response)

    result = classify_log(_make_parsed_log(error_line), client=mock_client)

    assert result["category"] == expected_category
    assert result["confidence"] == confidence
    assert result["root_cause_summary"]
    assert result["suggested_action"]
    return result


@pytest.mark.parametrize("log_text", CATEGORY_LOGS["next-tache-error"])
def test_classify_next_tache_error(log_text):
    _classify_with_mock(log_text, "next-tache-error")


@pytest.mark.parametrize("log_text", CATEGORY_LOGS["state-transition-block"])
def test_classify_state_transition_block(log_text):
    _classify_with_mock(log_text, "state-transition-block")


@pytest.mark.parametrize("log_text", CATEGORY_LOGS["provisioning-fault"])
def test_classify_provisioning_fault(log_text):
    _classify_with_mock(log_text, "provisioning-fault")


@pytest.mark.parametrize("log_text", CATEGORY_LOGS["api-integration-error"])
def test_classify_api_integration_error(log_text):
    _classify_with_mock(log_text, "api-integration-error")


@pytest.mark.parametrize("log_text", CATEGORY_LOGS["unclassified"])
def test_classify_unclassified(log_text):
    _classify_with_mock(log_text, "unclassified")


# --- Low-signal / garbage log → unclassified with non-empty reason ---

def test_garbage_log_returns_unclassified():
    garbage = "asdfghjkl random noise 12345 !@#$%"
    response = _make_llm_response("unclassified", confidence=30, reason="No meaningful content")
    mock_client = _mock_openai(response)

    result = classify_log(_make_parsed_log(garbage), client=mock_client)

    assert result["category"] == "unclassified"
    assert result["unclassified_reason"]


# --- Confidence <70% → forced unclassified ---

def test_low_confidence_forces_unclassified():
    response = _make_llm_response("provisioning-fault", confidence=55)
    mock_client = _mock_openai(response)

    result = classify_log(_make_parsed_log("some error"), client=mock_client)

    assert result["category"] == "unclassified"
    assert "55%" in result["unclassified_reason"]
    assert "below" in result["unclassified_reason"]


def test_confidence_exactly_70_not_forced():
    response = _make_llm_response("provisioning-fault", confidence=70)
    mock_client = _mock_openai(response)

    result = classify_log(_make_parsed_log("some error"), client=mock_client)

    assert result["category"] == "provisioning-fault"


# --- Input validation ---

def test_missing_raw_text_key_raises():
    with pytest.raises(ValueError, match="missing keys"):
        classify_log({"extracted_error_line": "error"})


def test_missing_extracted_error_line_key_raises():
    with pytest.raises(ValueError, match="missing keys"):
        classify_log({"raw_text": "raw"})


# --- LLM response parsing ---

def test_invalid_json_raises():
    mock_client = _mock_openai("not valid json {{{")
    with pytest.raises(RuntimeError, match="invalid JSON"):
        classify_log(_make_parsed_log("error"), client=mock_client)


def test_missing_keys_in_response_raises():
    response = json.dumps({"category": "unclassified"})
    mock_client = _mock_openai(response)
    with pytest.raises(RuntimeError, match="missing keys"):
        classify_log(_make_parsed_log("error"), client=mock_client)


# --- Output validation ---

def test_invalid_category_raises():
    response = _make_llm_response("made-up-category")
    mock_client = _mock_openai(response)
    with pytest.raises(RuntimeError, match="Invalid category"):
        classify_log(_make_parsed_log("error"), client=mock_client)


def test_confidence_out_of_range_raises():
    response = _make_llm_response("unclassified", confidence=150)
    mock_client = _mock_openai(response)
    with pytest.raises(RuntimeError, match="Confidence must be 0-100"):
        classify_log(_make_parsed_log("error"), client=mock_client)


def test_confidence_negative_raises():
    response = _make_llm_response("unclassified", confidence=-5)
    mock_client = _mock_openai(response)
    with pytest.raises(RuntimeError, match="Confidence must be 0-100"):
        classify_log(_make_parsed_log("error"), client=mock_client)


# --- Unit tests for internal helpers ---

def test_apply_confidence_rule_low():
    result = {"category": "provisioning-fault", "confidence": 60, "unclassified_reason": None}
    result = _apply_confidence_rule(result)
    assert result["category"] == "unclassified"
    assert "60%" in result["unclassified_reason"]


def test_apply_confidence_rule_high():
    result = {"category": "provisioning-fault", "confidence": 85, "unclassified_reason": None}
    result = _apply_confidence_rule(result)
    assert result["category"] == "provisioning-fault"
    assert result["unclassified_reason"] is None
