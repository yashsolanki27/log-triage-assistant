"""Tests for src/prompts.py — Unit 2 prompt template."""

from src.prompts import build_classification_prompt, CLASSIFICATION_PROMPT


def test_render_with_valid_log():
    prompt = build_classification_prompt("NullPointerException at line 42")
    assert "NullPointerException at line 42" in prompt
    assert "next-tache-error" in prompt
    assert "unclassified" in prompt


def test_render_includes_all_taxonomy_categories():
    prompt = build_classification_prompt("sample log")
    for cat in [
        "next-tache-error",
        "state-transition-block",
        "provisioning-fault",
        "api-integration-error",
        "unclassified",
    ]:
        assert cat in prompt


def test_render_includes_confidence_rule():
    prompt = build_classification_prompt("sample log")
    assert "< 70" in prompt or "<70" in prompt


def test_empty_log_raises():
    import pytest

    with pytest.raises(ValueError, match="non-empty"):
        build_classification_prompt("")


def test_whitespace_only_log_raises():
    import pytest

    with pytest.raises(ValueError, match="non-empty"):
        build_classification_prompt("   \n  \t  ")


def test_template_has_log_text_placeholder():
    assert "{log_text}" in CLASSIFICATION_PROMPT
