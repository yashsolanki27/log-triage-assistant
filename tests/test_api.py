"""Tests for src/api.py — Unit 4 API."""

import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.api import app

client = TestClient(app)


# --- Fixtures ---

def _mock_classify_response(
    category: str = "provisioning-fault",
    confidence: int = 85,
    reason: str | None = None,
) -> dict:
    return {
        "category": category,
        "root_cause_summary": f"Test summary for {category}",
        "confidence": confidence,
        "suggested_action": "Investigate the issue",
        "unclassified_reason": reason,
    }


# --- Valid input → 200 + correct schema ---


@patch("src.api.classify_log")
def test_triage_valid_input_returns_200(mock_classify):
    mock_classify.return_value = _mock_classify_response()

    response = client.post("/triage", json={"log_text": "DSLAM error on port 3/0/12"})

    assert response.status_code == 200
    data = response.json()
    assert data["category"] == "provisioning-fault"
    assert data["confidence"] == 85
    assert "root_cause_summary" in data
    assert "suggested_action" in data
    assert "unclassified_reason" in data


@patch("src.api.classify_log")
def test_triage_valid_input_schema_matches_response_model(mock_classify):
    mock_classify.return_value = _mock_classify_response()

    response = client.post("/triage", json={"log_text": "NullPointerException at OrderProcessor.java:142"})

    data = response.json()
    required_keys = {"category", "root_cause_summary", "confidence", "suggested_action", "unclassified_reason"}
    assert required_keys == set(data.keys())


@patch("src.api.classify_log")
def test_triage_unclassified_result_returns_200(mock_classify):
    mock_classify.return_value = _mock_classify_response(
        category="unclassified",
        confidence=45,
        reason="No meaningful error pattern detected",
    )

    response = client.post("/triage", json={"log_text": "System running normally"})

    assert response.status_code == 200
    data = response.json()
    assert data["category"] == "unclassified"
    assert data["unclassified_reason"] == "No meaningful error pattern detected"


# --- Empty / missing log_text → 422 ---


def test_triage_empty_log_text_returns_422():
    response = client.post("/triage", json={"log_text": ""})
    assert response.status_code == 422


def test_triage_missing_log_text_returns_422():
    response = client.post("/triage", json={})
    assert response.status_code == 422


def test_triage_no_body_returns_422():
    response = client.post("/triage")
    assert response.status_code == 422


# --- Integration: parser ValueError → 422 ---


def test_triage_whitespace_only_log_text_returns_422():
    response = client.post("/triage", json={"log_text": "   "})
    assert response.status_code == 422


# --- Regression: RuntimeError from classifier → 500 with detail ---

@patch("src.api.classify_log")
def test_triage_classifier_runtime_error_returns_500(mock_classify):
    mock_classify.side_effect = RuntimeError("LLM returned invalid JSON: garbage")

    response = client.post("/triage", json={"log_text": "some log text"})

    assert response.status_code == 500
    data = response.json()
    assert "Classification failed" in data["detail"]
    assert "LLM returned invalid JSON" in data["detail"]


@patch("src.api.classify_log")
def test_triage_classifier_missing_api_key_returns_500(mock_classify):
    mock_classify.side_effect = RuntimeError("OPENCODE_API_KEY environment variable not set")

    response = client.post("/triage", json={"log_text": "some log text"})

    assert response.status_code == 500
    data = response.json()
    assert "OPENCODE_API_KEY" in data["detail"]


@patch("src.api.classify_log")
def test_triage_classifier_invalid_category_returns_500(mock_classify):
    mock_classify.side_effect = RuntimeError("Invalid category: bogus")

    response = client.post("/triage", json={"log_text": "some log text"})

    assert response.status_code == 500
    data = response.json()
    assert "Invalid category" in data["detail"]
