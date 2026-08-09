"""Tests for src/classifier.py — Unit 3 classifier (non-LLM logic)."""

import os
from unittest.mock import MagicMock, patch

import pytest

from openai import AuthenticationError, RateLimitError

from src.classifier import (
    _apply_confidence_rule,
    _get_api_keys,
    _parse_llm_json,
    classify_log,
)


def test_parse_valid_json():
    text = (
        '{"category": "next-tache-error", "root_cause_summary": "x", '
        '"confidence": 90, "suggested_action": "y"}'
    )
    result = _parse_llm_json(text)
    assert result["category"] == "next-tache-error"
    assert result["unclassified_reason"] is None


def test_parse_json_strips_markdown_fence():
    text = (
        '```json\n{"category": "provisioning-fault", "root_cause_summary": "x", '
        '"confidence": 80, "suggested_action": "y"}\n```'
    )
    result = _parse_llm_json(text)
    assert result["category"] == "provisioning-fault"


def test_parse_json_missing_field_raises():
    text = '{"category": "provisioning-fault", "confidence": 80}'
    with pytest.raises(RuntimeError, match="missing required fields"):
        _parse_llm_json(text)


def test_parse_non_json_raises():
    with pytest.raises(RuntimeError, match="non-JSON"):
        _parse_llm_json("not json at all")


def test_confidence_rule_high_confidence_kept():
    result = _apply_confidence_rule(
        {"category": "api-integration-error", "confidence": 88, "unclassified_reason": None}
    )
    assert result["category"] == "api-integration-error"
    assert result["unclassified_reason"] is None


def test_confidence_rule_low_confidence_forced_unclassified():
    result = _apply_confidence_rule(
        {"category": "state-transition-block", "confidence": 55, "unclassified_reason": None}
    )
    assert result["category"] == "unclassified"
    assert "55" in result["unclassified_reason"]
    assert "70" in result["unclassified_reason"]


def test_confidence_rule_boundary_70_is_not_forced():
    result = _apply_confidence_rule(
        {"category": "provisioning-fault", "confidence": 70, "unclassified_reason": None}
    )
    assert result["category"] == "provisioning-fault"


def test_confidence_rule_invalid_category_forced_unclassified():
    result = _apply_confidence_rule(
        {"category": "not-a-real-category", "confidence": 95, "unclassified_reason": None}
    )
    assert result["category"] == "unclassified"
    assert "not-a-real-category" in result["unclassified_reason"]


def test_confidence_rule_preserves_existing_unclassified_reason():
    result = _apply_confidence_rule(
        {
            "category": "unclassified",
            "confidence": 40,
            "unclassified_reason": "Log too sparse to classify.",
        }
    )
    assert result["unclassified_reason"] == "Log too sparse to classify."


# ---------------------------------------------------------------------------
# Multi-key failover (_get_api_keys + rotation in classify_log)
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_classifier_state():
    """Clear cached client + key index between tests (module-level globals)."""
    import src.classifier as classifier

    classifier._client = None
    classifier._key_index = 0
    yield
    classifier._client = None
    classifier._key_index = 0


def test_get_api_keys_splits_comma_separated(monkeypatch):
    monkeypatch.setenv("OPENCODE_API_KEY", "key-one, key-two ,key-three")
    assert _get_api_keys() == ["key-one", "key-two", "key-three"]


def test_get_api_keys_single_key(monkeypatch):
    monkeypatch.setenv("OPENCODE_API_KEY", "only-key")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert _get_api_keys() == ["only-key"]


def test_get_api_keys_falls_back_to_openai_key(monkeypatch):
    monkeypatch.delenv("OPENCODE_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "openai-fallback")
    assert _get_api_keys() == ["openai-fallback"]


def _mock_result_payload(category="next-tache-error", confidence=90):
    return {
        "category": category,
        "root_cause_summary": "Root cause",
        "confidence": confidence,
        "suggested_action": "Act",
        "unclassified_reason": None,
    }


def _client_that_fails_with(exc_class):
    client = MagicMock()
    client.chat.completions.create.side_effect = _make_openai_error(exc_class)
    return client


def _make_openai_error(exc_class):
    import httpx

    response = httpx.Response(status_code=429, request=httpx.Request("POST", "http://test"))
    return exc_class(
        message="rate limited",
        response=response,
        body=None,
    )


def test_classify_rotates_to_next_key_on_auth_error(monkeypatch):
    """Rate-limited first key -> second key succeeds."""
    first = _client_that_fails_with(AuthenticationError)
    second = MagicMock()
    payload = _mock_result_payload()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="{}"))]
    second.chat.completions.create.return_value = mock_response

    keys = ["bad-key", "good-key"]
    calls = {"n": 0}

    def fake_build_client(api_key):
        calls["n"] += 1
        return first if api_key == "bad-key" else second

    parsed = {"raw_text": "ERROR sample", "extracted_error_line": "ERROR sample"}
    with (
        patch("src.classifier._get_api_keys", return_value=keys),
        patch("src.classifier._build_client", side_effect=fake_build_client),
        patch("src.classifier._parse_llm_json", return_value=payload),
        patch("src.classifier._apply_confidence_rule", side_effect=lambda r: r),
    ):
        result = classify_log(parsed)

    assert result == payload
    assert calls["n"] == 2  # first client built for bad key, second for good key


def test_classify_raises_when_all_keys_fail(monkeypatch):
    """Every key rate-limited -> RuntimeError, not a silent fallback."""
    parsed = {"raw_text": "ERROR sample", "extracted_error_line": "ERROR sample"}

    keys = ["bad-key-1", "bad-key-2"]

    def fake_build_client(api_key):
        return _client_that_fails_with(RateLimitError)

    with (
        patch("src.classifier._get_api_keys", return_value=keys),
        patch("src.classifier._build_client", side_effect=fake_build_client),
        patch("src.classifier._parse_llm_json", return_value={}),
        patch("src.classifier._apply_confidence_rule", side_effect=lambda r: r),
    ):
        with pytest.raises(RuntimeError, match="All configured LLM API keys failed"):
            classify_log(parsed)


def test_classify_single_key_failure_raises(monkeypatch):
    """With only one key, a rate-limit error surfaces as RuntimeError."""
    parsed = {"raw_text": "ERROR sample", "extracted_error_line": "ERROR sample"}

    with (
        patch("src.classifier._get_api_keys", return_value=["only-key"]),
        patch("src.classifier._build_client", side_effect=lambda k: _client_that_fails_with(RateLimitError)),
        patch("src.classifier._parse_llm_json", return_value={}),
        patch("src.classifier._apply_confidence_rule", side_effect=lambda r: r),
    ):
        with pytest.raises(RuntimeError, match="All configured LLM API keys failed"):
            classify_log(parsed)
