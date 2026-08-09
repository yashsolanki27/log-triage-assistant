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

## Data flow

1. Browser SPA posts raw log text to `POST /triage`.
2. `src/parser.py` extracts the most diagnostic error line.
3. `src/classifier.py` calls the LLM with the prompt from `src/prompts.py`.
4. `src/db.py` persists the result; the API returns it to the SPA.
5. `GET /history` and `GET /stats` power the History and Dashboard screens.

## Endpoints

| Method | Path          | Purpose                                   |
|--------|---------------|-------------------------------------------|
| POST   | /triage       | Classify a log entry                      |
| GET    | /history      | List past triages (filter, paginate)      |
| GET    | /triage/{id}  | Single triage by ID                       |
| GET    | /stats        | Dashboard aggregates                      |
| GET    | /sample-logs  | Sample logs from data/sample_logs.py      |
| GET    | /health       | Liveness probe (used by Railway)          |
| GET    | /             | SPA frontend (index.html)                 |
