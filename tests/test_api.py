"""Tests for src/api.py — Unit 4 API layer.

Uses a mocked classifier so these run without OPENCODE_API_KEY or network
access, and against a scratch SQLite DB so they don't pollute real data.
"""

import importlib
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

FAKE_RESULT = {
    "category": "next-tache-error",
    "root_cause_summary": "Null pointer during order processing calc step.",
    "confidence": 92,
    "suggested_action": "Add a null guard around getStatus().",
    "unclassified_reason": None,
}


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """Fresh app + fresh on-disk SQLite DB per test."""
    from src import db as db_module

    monkeypatch.setattr(db_module, "DB_PATH", tmp_path / "test_triage.db")

    import src.api as api_module

    importlib.reload(api_module)

    with patch("src.api.classify_log", return_value=dict(FAKE_RESULT)):
        with TestClient(api_module.app) as c:
            yield c


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "db_path" in data


def test_triage_success(client):
    r = client.post(
        "/triage",
        json={"log_text": "java.lang.NullPointerException: x\n at Foo.bar(Foo.java:1)"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["category"] == "next-tache-error"
    assert data["extracted_error_line"].startswith("java.lang.NullPointerException")
    assert "id" in data and "created_at" in data


def test_triage_empty_log_returns_422(client):
    r = client.post("/triage", json={"log_text": "   "})
    assert r.status_code == 422


def test_triage_missing_field_returns_422(client):
    r = client.post("/triage", json={})
    assert r.status_code == 422


def test_triage_log_too_long_returns_422(client):
    r = client.post("/triage", json={"log_text": "ERROR " + "x" * 20000})
    assert r.status_code == 422


def test_triage_log_at_max_length_ok(client):
    r = client.post("/triage", json={"log_text": "x" * 20000})
    assert r.status_code == 200, r.text


def test_history_returns_saved_triages(client):
    client.post("/triage", json={"log_text": "ERROR one"})
    client.post("/triage", json={"log_text": "ERROR two"})
    r = client.get("/history")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_history_filters_by_category(client):
    client.post("/triage", json={"log_text": "ERROR one"})
    r = client.get("/history?category=next-tache-error")
    assert r.status_code == 200
    assert len(r.json()) == 1
    r = client.get("/history?category=provisioning-fault")
    assert r.status_code == 200
    assert len(r.json()) == 0


def test_get_triage_by_id(client):
    posted = client.post("/triage", json={"log_text": "ERROR one"}).json()
    r = client.get(f"/triage/{posted['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == posted["id"]


def test_get_triage_missing_id_returns_404(client):
    r = client.get("/triage/999999")
    assert r.status_code == 404


def test_stats_shape(client):
    client.post("/triage", json={"log_text": "ERROR one"})
    r = client.get("/stats")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 1
    assert "next-tache-error" in data["by_category"]
    assert "trend" in data


def test_frontend_served_at_root(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "LogPulse" in r.text


def test_static_assets_served(client):
    r = client.get("/assets/styles.css")
    assert r.status_code == 200
    r = client.get("/assets/app.js")
    assert r.status_code == 200


def test_sample_logs_returns_list(client):
    r = client.get("/sample-logs")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) > 0
    first = data[0]
    assert "title" in first
    assert "category" in first
    assert "tag" in first
    assert "log_text" in first
    assert isinstance(first["title"], str)
    assert isinstance(first["log_text"], str)
    assert len(first["log_text"]) > 0


def test_sample_logs_has_all_entries(client):
    from data.sample_logs import SAMPLE_LOGS

    r = client.get("/sample-logs")
    data = r.json()
    assert len(data) == len(SAMPLE_LOGS)


def test_sample_logs_entries_have_valid_fields(client):
    from src.classifier import VALID_CATEGORIES

    r = client.get("/sample-logs")
    data = r.json()
    for entry in data:
        assert entry["title"], f"Empty title in entry: {entry}"
        assert entry["tag"], f"Empty tag in entry: {entry['title']}"
        assert entry["log_text"], f"Empty log_text in entry: {entry['title']}"
        assert entry["category"] in VALID_CATEGORIES, (
            f"Invalid category in entry: {entry['title']}"
        )
