"""Storage layer for triage results.

docs/tech-stack.md marks storage as "none needed v1 — stateless classify-in,
result-out". This module is a deliberate v1.1 extension to support the
History and Dashboard screens (see docs/architecture.md addendum). Kept
isolated behind a small interface so the stateless core (parser, prompts,
classifier) stays untouched — patterns.md: one function, one responsibility.
"""

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

_DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "triage.db"
DB_PATH = Path(os.environ.get("TRIAGE_DB_PATH", str(_DEFAULT_DB_PATH)))

SCHEMA = """
CREATE TABLE IF NOT EXISTS triages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    raw_text TEXT NOT NULL,
    extracted_error_line TEXT NOT NULL,
    category TEXT NOT NULL,
    root_cause_summary TEXT NOT NULL,
    confidence INTEGER NOT NULL,
    suggested_action TEXT NOT NULL,
    unclassified_reason TEXT
);
"""


@contextmanager
def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with _connect() as conn:
        conn.execute(SCHEMA)


def save_triage(parsed: dict, result: dict) -> dict:
    """Persist a completed triage (parser output + classifier output)."""
    created_at = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO triages (
                created_at, raw_text, extracted_error_line, category,
                root_cause_summary, confidence, suggested_action, unclassified_reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                created_at,
                parsed["raw_text"],
                parsed["extracted_error_line"],
                result["category"],
                result["root_cause_summary"],
                result["confidence"],
                result["suggested_action"],
                result.get("unclassified_reason"),
            ),
        )
        row_id = cursor.lastrowid

    return {
        "id": row_id,
        "created_at": created_at,
        "raw_text": parsed["raw_text"],
        "extracted_error_line": parsed["extracted_error_line"],
        **result,
    }


def list_triages(limit: int = 100, offset: int = 0, category: str | None = None) -> list[dict]:
    query = "SELECT * FROM triages"
    params: list = []
    if category:
        query += " WHERE category = ?"
        params.append(category)
    query += " ORDER BY id DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    with _connect() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def get_triage(triage_id: int) -> dict | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM triages WHERE id = ?", (triage_id,)).fetchone()
    return dict(row) if row else None


def get_stats() -> dict:
    """Aggregate counts for the dashboard: totals, per-category breakdown,
    unclassified rate, and a daily trend for the last 14 days."""
    with _connect() as conn:
        total = conn.execute("SELECT COUNT(*) AS c FROM triages").fetchone()["c"]

        by_category_rows = conn.execute(
            "SELECT category, COUNT(*) AS c, AVG(confidence) AS avg_conf "
            "FROM triages GROUP BY category"
        ).fetchall()

        trend_rows = conn.execute(
            """
            SELECT substr(created_at, 1, 10) AS day, COUNT(*) AS c
            FROM triages
            GROUP BY day
            ORDER BY day DESC
            LIMIT 14
            """
        ).fetchall()

    by_category = {
        row["category"]: {
            "count": row["c"],
            "avg_confidence": round(row["avg_conf"], 1) if row["avg_conf"] is not None else 0,
        }
        for row in by_category_rows
    }
    unclassified_count = by_category.get("unclassified", {}).get("count", 0)

    return {
        "total": total,
        "unclassified_count": unclassified_count,
        "unclassified_rate": round(unclassified_count / total * 100, 1) if total else 0,
        "by_category": by_category,
        "trend": list(reversed([{"day": r["day"], "count": r["c"]} for r in trend_rows])),
    }
