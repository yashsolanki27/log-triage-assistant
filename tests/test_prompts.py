"""Tests for src/prompts.py — Unit 2 prompt template."""

from pathlib import Path

from src.prompts import build_classification_prompt, CLASSIFICATION_PROMPT

REPO_ROOT = Path(__file__).resolve().parents[1]
BUSINESS_LOGIC_DOC = REPO_ROOT / "docs" / "business-logic.md"

# Expanded-taxonomy expectation: each category must carry signal keywords and
# at least one example log line in both the prompt and the mirrored doc.
# (tech-debt item #9 — regression fence so a rewrite can't strip them again.)
EXPECTED_SIGNALS = {
    "next-tache-error": [
        "Next Tache error",
        "Tache sequence broken",
        "started before prerequisite",
        "OrderEngine",
    ],
    "state-transition-block": [
        "collaborative_wait_time",
        "refire_count",
        "masterless",
        "stuck in state",
    ],
    "provisioning-fault": [
        "DSLAM",
        "node_id",
        "expected_fw",
        "Provisioning rejected",
    ],
    "api-integration-error": [
        "SOAP envelope",
        "schema validation",
        "token expired",
        "Query timeout",
    ],
    "unclassified": [
        "no error signals",
        "flag for human review",
    ],
}

EXPECTED_EXAMPLE_FRAGMENTS = {
    "next-tache-error": "Tache sequence broken at step 3/7",
    "state-transition-block": "collaborative_wait_time=45s exceeded threshold",
    "provisioning-fault": "expected_fw=v4.2 actual_fw=v4.0",
    "api-integration-error": "SOAP envelope missing namespace declaration",
    "unclassified": "Health ping received from node lb-01",
}


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


def test_prompt_taxonomy_has_signal_keywords_for_every_category():
    """Every taxonomy category in the prompt must carry signal keywords
    (tech-debt item #9 fence)."""
    prompt = build_classification_prompt("sample log")
    for cat, signals in EXPECTED_SIGNALS.items():
        assert cat in prompt, f"missing category {cat} in prompt"
        for signal in signals:
            assert signal in prompt, f"category {cat}: missing signal {signal!r}"


def test_prompt_taxonomy_has_example_log_line_for_every_category():
    """Every taxonomy category in the prompt must include an example log line
    so the model can match signals to real-world text (tech-debt item #9)."""
    prompt = build_classification_prompt("sample log")
    for cat, fragment in EXPECTED_EXAMPLE_FRAGMENTS.items():
        assert fragment in prompt, f"category {cat}: missing example fragment {fragment!r}"


def test_business_logic_doc_mirrors_prompt_taxonomy():
    """docs/business-logic.md must mirror the prompt's expanded taxonomy:
    every category carries signal keywords, distinguishing features, and
    example log lines (tech-debt item #9 fence)."""
    doc = BUSINESS_LOGIC_DOC.read_text(encoding="utf-8")
    assert doc, "docs/business-logic.md is empty"
    for cat, signals in EXPECTED_SIGNALS.items():
        assert f"`{cat}`" in doc, f"docs missing category section {cat}"
        for signal in signals:
            assert signal in doc, f"docs category {cat}: missing signal {signal!r}"
    for section in ("**Signal keywords:**", "**Distinguishing features:**", "**Example log lines:**"):
        assert section in doc, f"docs missing section {section}"
    for cat, fragment in EXPECTED_EXAMPLE_FRAGMENTS.items():
        assert fragment in doc, f"docs category {cat}: missing example {fragment!r}"
