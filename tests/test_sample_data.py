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
