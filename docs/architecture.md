# Architecture

log file/text → parser (extract error line + context)
→ classifier (LLM call, business-logic.md taxonomy)
→ FastAPI endpoint returns {category, root_cause_summary, confidence}
→ vanilla JS SPA (web/) displays result; SQLite (src/db.py) stores history

Parser logic: src/parser.py
Classifier logic: src/classifier.py
Prompt templates: src/prompts.py
API layer: src/api.py (also serves the SPA from /web at "/")
Storage layer: src/db.py (SQLite, defaults to data/triage.db)

## TriageResult response contract

The `TriageResult` model (src/api.py) is the single response shape for
`POST /triage`, `GET /history`, and `GET /triage/{id}`. It self-enforces the
business-logic.md `unclassified_reason` rule via a `model_validator`:
category `unclassified` requires a non-empty `unclassified_reason`, every
other category requires `null`. Any result that violates this is rejected at
the response boundary (HTTP 500), so the contract holds regardless of how a
result is produced.

## Data flow

1. Browser SPA posts raw log text to `POST /triage`.
2. `src/parser.py` extracts the most diagnostic error line.
3. `src/classifier.py` calls the LLM with the prompt from `src/prompts.py`.
4. `src/db.py` persists the result; the API returns it to the SPA.
5. `GET /history` and `GET /stats` power the History and Dashboard screens.

## Endpoints

| Method | Path          | Purpose                                   |
|--------|---------------|-------------------------------------------|
| POST   | /triage       | Classify a log entry (1-20000 chars)      |
| GET    | /history      | List past triages (filter, paginate)      |
| GET    | /triage/{id}  | Single triage by ID                       |
| GET    | /stats        | Dashboard aggregates                      |
| GET    | /sample-logs  | Sample logs from data/sample_logs.py      |
| GET    | /health       | Liveness probe — status, version, db_path |
| GET    | /             | SPA frontend (index.html)                 |
