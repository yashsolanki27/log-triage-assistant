"""Tests for src/classifier.py — Unit 3 classifier (non-LLM logic)."""

import pytest

from src.classifier import _apply_confidence_rule, _parse_llm_json


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
