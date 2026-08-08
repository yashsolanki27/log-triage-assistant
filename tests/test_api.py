"""Tests for src/api.py — Unit 4 API layer.

Uses a mocked classifier so these run without ANTHROPIC_API_KEY or network
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
    assert r.json() == {"status": "ok"}


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
    assert "Log Triage Assistant" in r.text


def test_static_assets_served(client):
    r = client.get("/assets/styles.css")
    assert r.status_code == 200
    r = client.get("/assets/app.js")
    assert r.status_code == 200
