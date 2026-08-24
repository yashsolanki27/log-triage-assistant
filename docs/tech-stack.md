# Tech Stack

- Backend: Python 3.11+, FastAPI, Uvicorn
- LLM: OpenAI SDK against an OpenAI-compatible endpoint (Groq / OpenCode Zen / OpenAI), single classification call per log entry
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

| Variable           | Default                                            | Required |
|--------------------|----------------------------------------------------|----------|
| GROQ_API_KEY       | —                                                  | Optional (Recommended free provider) |
| OPENCODE_API_KEY   | —                                                  | Optional (falls back to OPENAI_API_KEY) |
| OPENAI_API_KEY     | —                                                  | Optional |
| GROQ_BASE_URL      | https://api.groq.com/openai/v1                     | No |
| OPENCODE_BASE_URL  | https://opencode.ai/zen/v1                         | No |
| LLM_MODEL_NAME     | llama-3.3-70b-versatile (Groq) / deepseek-v4-flash-free (OpenCode) | No |
| LLM_TIMEOUT        | 30.0                                               | No |
| TRIAGE_DB_PATH     | ./data/triage.db                                   | No (set to a persistent volume in prod) |

### Multi-key failover

API key variables accept a comma-separated list (`key1,key2,key3`). The
classifier tries the first key; on any API/auth/rate-limit error (400, 401, 429, 500)
it automatically rebuilds the client with the next key and retries. If every
key fails, the request returns HTTP 502. This is enforced in
`src/classifier.py` (`_get_api_keys` + `_rotate_key`).
