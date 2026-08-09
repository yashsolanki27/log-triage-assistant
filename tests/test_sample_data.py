"""Tests for data/sample_logs.py — Sample log data integrity.

Ensures every sample log entry is valid and consistent with the
classifier taxonomy.
"""

import pytest

from data.sample_logs import CATEGORIES, SAMPLE_LOGS
from src.classifier import VALID_CATEGORIES


def test_categories_match_classifier_taxonomy():
    """CATEGORIES keys must exactly match the classifier's valid set."""
    assert set(CATEGORIES.keys()) == VALID_CATEGORIES


def test_sample_logs_is_non_empty_list():
    assert isinstance(SAMPLE_LOGS, list)
    assert len(SAMPLE_LOGS) > 0


def test_every_entry_has_required_keys():
    required = {"title", "category", "tag", "log"}
    for entry in SAMPLE_LOGS:
        missing = required - set(entry.keys())
        assert not missing, f"Entry '{entry.get('title', '?')}' missing keys: {missing}"


def test_every_entry_has_non_empty_title():
    for entry in SAMPLE_LOGS:
        assert entry["title"], f"Empty title in entry: {entry}"


def test_every_entry_has_non_empty_log():
    for entry in SAMPLE_LOGS:
        assert entry["log"], f"Empty log in entry: {entry['title']}"


def test_every_category_is_valid():
    for entry in SAMPLE_LOGS:
        assert entry["category"] in VALID_CATEGORIES, (
            f"Entry '{entry['title']}' has invalid category: {entry['category']}"
        )


def test_all_four_error_categories_represented():
    cats = {e["category"] for e in SAMPLE_LOGS}
    expected = {"next-tache-error", "state-transition-block", "provisioning-fault", "api-integration-error"}
    assert expected.issubset(cats), f"Missing categories: {expected - cats}"


def test_no_duplicate_titles():
    titles = [e["title"] for e in SAMPLE_LOGS]
    dupes = [t for t in titles if titles.count(t) > 1]
    assert not dupes, f"Duplicate titles: {set(dupes)}"


def test_minimum_log_length():
    for entry in SAMPLE_LOGS:
        assert len(entry["log"]) >= 20, (
            f"Log too short ({len(entry['log'])} chars) in '{entry['title']}'"
        )


def test_each_error_category_has_minimum_samples():
    """Every error category needs enough samples for a meaningful live-LLM
    benchmark (the 25-case test: 5 logs x 5 categories)."""
    min_per_category = 5
    from collections import Counter

    counts = Counter(e["category"] for e in SAMPLE_LOGS)
    for cat in VALID_CATEGORIES - {"unclassified"}:
        assert counts[cat] >= min_per_category, (
            f"Category '{cat}' has only {counts[cat]} samples; "
            f"need at least {min_per_category}"
        )


def test_unclassified_has_benchmark_samples():
    """unclassified also needs the same minimum so the 5x5 benchmark holds."""
    from collections import Counter

    counts = Counter(e["category"] for e in SAMPLE_LOGS)
    assert counts["unclassified"] >= 5, (
        f"Category 'unclassified' has only {counts['unclassified']} samples"
    )


def test_tag_implies_consistent_category():
    """A given error tag must not map to contradicting categories."""
    mapping = {}
    for entry in SAMPLE_LOGS:
        prev = mapping.setdefault(entry["tag"], entry["category"])
        assert prev == entry["category"], (
            f"Tag '{entry['tag']}' maps to both '{prev}' and '{entry['category']}'"
        )
