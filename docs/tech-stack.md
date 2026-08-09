# Tech Stack

- Backend: Python 3.11+, FastAPI, Uvicorn
- LLM: OpenAI SDK against an OpenAI-compatible endpoint (default: OpenCode Zen / DeepSeek V4 Flash Free), single classification call per log entry
- Frontend: vanilla HTML/CSS/JS SPA (web/) — dark theme, no build step
- Alternative UI: Streamlit (streamlit_app.py + app_pages/), deprecated but kept
- Storage: SQLite via stdlib sqlite3 — data/triage.db by default, overridable with `TRIAGE_DB_PATH`
- Sample data: data/sample_logs.py (single source of truth; served via /sample-logs)
- Testing: pytest (live LLM tests excluded by default via `-m "not live"`)
- Hosting: Railway (railway.json + Procfile), health check at /health

## Input assumptions

- Log input to `parse_log` (and `POST /triage`) is assumed to be valid Unicode
  text (UTF-8 decoded). The parser rejects NUL bytes (`\x00`) — a marker of
  binary/garbled data — with a 422 `ValueError`; other non-UTF-8 sequences are
  filtered upstream by the JSON decoder.

## Environment variables

| Variable           | Default                         | Required |
|--------------------|---------------------------------|----------|
| OPENCODE_API_KEY   | —                               | Yes (falls back to OPENAI_API_KEY) |
| OPENCODE_BASE_URL  | https://opencode.ai/zen/v1      | No |
| LLM_MODEL_NAME     | deepseek-v4-flash-free          | No |
| TRIAGE_DB_PATH     | ./data/triage.db                | No (set to a persistent volume in prod) |

### Multi-key failover

`OPENCODE_API_KEY` accepts a comma-separated list (`key1,key2,key3`). The
classifier tries the first key; on an auth error (401) or rate-limit (429)
it automatically rebuilds the client with the next key and retries. If every
key fails, the request returns HTTP 502. This is enforced in
`src/classifier.py` (`_get_api_keys` + `_rotate_key`).
