"""Tests for src/db.py — Storage layer.

Uses a shared in-memory SQLite connection per test for isolation.
"""

import sqlite3
from contextlib import contextmanager
from unittest.mock import patch

import pytest

from src import db as db_module


@pytest.fixture()
def db():
    """Fresh in-memory SQLite DB per test using a shared connection."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row

    @contextmanager
    def _test_connect():
        try:
            yield conn
            conn.commit()
        finally:
            pass  # don't close — shared across calls

    original = db_module._connect
    db_module._connect = _test_connect
    db_module.init_db()
    yield db_module
    db_module._connect = original
    conn.close()


def _make_parsed(raw="ERROR test log", extracted="ERROR test log"):
    return {"raw_text": raw, "extracted_error_line": extracted}


def _make_result(category="next-tache-error", confidence=90):
    return {
        "category": category,
        "root_cause_summary": "Test root cause",
        "confidence": confidence,
        "suggested_action": "Test action",
        "unclassified_reason": None,
    }


def test_init_db_no_error(db):
    db.init_db()


def test_save_triage_returns_correct_shape(db):
    result = db.save_triage(_make_parsed(), _make_result())
    assert "id" in result
    assert "created_at" in result
    assert result["category"] == "next-tache-error"
    assert result["confidence"] == 90
    assert result["raw_text"] == "ERROR test log"


def test_save_triage_increments_id(db):
    r1 = db.save_triage(_make_parsed("log1"), _make_result())
    r2 = db.save_triage(_make_parsed("log2"), _make_result())
    assert r2["id"] > r1["id"]


def test_get_triage_returns_saved(db):
    saved = db.save_triage(_make_parsed(), _make_result())
    fetched = db.get_triage(saved["id"])
    assert fetched is not None
    assert fetched["id"] == saved["id"]
    assert fetched["raw_text"] == "ERROR test log"


def test_get_triage_returns_none_for_missing(db):
    assert db.get_triage(999999) is None


def test_list_triages_returns_all(db):
    db.save_triage(_make_parsed("a"), _make_result())
    db.save_triage(_make_parsed("b"), _make_result())
    items = db.list_triages()
    assert len(items) == 2


def test_list_triages_respects_limit(db):
    for i in range(5):
        db.save_triage(_make_parsed(f"log{i}"), _make_result())
    items = db.list_triages(limit=3)
    assert len(items) == 3


def test_list_triages_respects_offset(db):
    for i in range(5):
        db.save_triage(_make_parsed(f"log{i}"), _make_result())
    items = db.list_triages(offset=3)
    assert len(items) == 2


def test_list_triages_filters_by_category(db):
    db.save_triage(_make_parsed("a"), _make_result("next-tache-error"))
    db.save_triage(_make_parsed("b"), _make_result("provisioning-fault"))
    items = db.list_triages(category="next-tache-error")
    assert len(items) == 1
    assert items[0]["category"] == "next-tache-error"


def test_list_triages_empty(db):
    assert db.list_triages() == []


def test_get_stats_empty_db(db):
    stats = db.get_stats()
    assert stats["total"] == 0
    assert stats["unclassified_count"] == 0
    assert stats["unclassified_rate"] == 0
    assert stats["by_category"] == {}
    assert stats["trend"] == []


def test_get_stats_with_data(db):
    db.save_triage(_make_parsed("a"), _make_result("next-tache-error", 95))
    db.save_triage(_make_parsed("b"), _make_result("provisioning-fault", 80))
    db.save_triage(_make_parsed("c"), _make_result("unclassified", 50))
    stats = db.get_stats()
    assert stats["total"] == 3
    assert stats["unclassified_count"] == 1
    assert abs(stats["unclassified_rate"] - 33.3) < 0.1
    assert "next-tache-error" in stats["by_category"]
    assert stats["by_category"]["next-tache-error"]["count"] == 1
    assert stats["by_category"]["next-tache-error"]["avg_confidence"] == 95.0
    assert len(stats["trend"]) >= 1


def test_get_stats_trend_sorted_by_day(db):
    db.save_triage(_make_parsed("a"), _make_result())
    stats = db.get_stats()
    if len(stats["trend"]) > 1:
        days = [t["day"] for t in stats["trend"]]
        assert days == sorted(days)


def test_save_triage_with_unclassified_reason(db):
    result = _make_result("unclassified", 50)
    result["unclassified_reason"] = "Low confidence"
    saved = db.save_triage(_make_parsed(), result)
    fetched = db.get_triage(saved["id"])
    assert fetched["unclassified_reason"] == "Low confidence"
