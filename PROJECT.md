# PROJECT.md — LogPulse (OSS/BSS Log Classifier)

## What this project does

A tool that takes raw OSS/BSS log entries (from telecom order processing,
provisioning, and API integration systems), classifies the error pattern using
an LLM, and suggests a root cause and next action. It automates manual RCA
triage work for application support engineers.

**Target user:** Telecom / OSS-BSS application support engineers who manually
read logs, identify error patterns, and determine next steps.

---

## Architecture

```
User pastes log text
       │
       ▼
┌─────────────┐     ┌────────────────┐     ┌──────────────────┐
│   Parser     │────▶│   Classifier   │────▶│   FastAPI + SQLite│
│ src/parser.py│     │src/classifier.py│    │     src/api.py    │
└─────────────┘     └────────────────┘     └──────┬───────────┘
                                                    │
                                                    ▼
                                      ┌─────────────────────────┐
                                      │  Vanilla JS SPA (web/)   │
                                      │  Triage · History · Dash  │
                                      └─────────────────────────┘
```

### Data flow

1. **Parser** (`src/parser.py`) — Extracts the error line from raw log text.
   Cleans noise, prioritizes exception lines over generic error markers.
   Output: `{raw_text, extracted_error_line}`

2. **Prompt template** (`src/prompts.py`) — LLM prompt referencing the
   taxonomy in `docs/business-logic.md`. Stored separately (not inline).

3. **Classifier** (`src/classifier.py`) — Calls LLM with the prompt.
   Output: `{category, root_cause_summary, confidence, suggested_action, unclassified_reason}`
   Confidence <70% forces category to `unclassified`.

4. **API** (`src/api.py`) — FastAPI `POST /triage` endpoint, plus
   `GET /history`, `GET /triage/{id}`, `GET /stats`, `GET /sample-logs`,
   `GET /health`. Serves the SPA at `/`.

5. **UI** (`web/index.html` + `web/styles.css` + `web/app.js`) — Vanilla
   HTML/CSS/JS SPA, dark theme, hash routing across three screens:
   Triage (paste → classify → result), History (filterable list),
   Dashboard (category donut + 14-day trend).

---

## Error categories (5 total)

| Category | Label | What it catches |
|----------|-------|-----------------|
| `next-tache-error` | Task sequencing | Task started before prerequisite completed |
| `state-transition-block` | Stuck order | Order/subscriber stuck in a state |
| `provisioning-fault` | Config / node failure | DSLAM/LMG/OLT provisioning rejected |
| `api-integration-error` | API failure | REST/SOAP integration failed |
| `unclassified` | Needs review | No confident match — flagged for human review |

Full taxonomy with signal keywords, examples, and decision flowchart:
see `docs/business-logic.md`

---

## Tech stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| Backend | Python 3.11+, FastAPI | `src/api.py` |
| LLM | OpenCode Zen (DeepSeek V4 Flash Free) | Single classification call |
| Frontend | Vanilla HTML/CSS/JS SPA | `web/` — dark theme, no build step |
| Storage | SQLite (stdlib) | `data/triage.db`, override via `TRIAGE_DB_PATH` |
| Testing | pytest | 82 tests, all passing (70 unit + 12 live, opt-in) |
| Hosting | Railway | `railway.json` + `Procfile` |

### Environment variables

| Variable | Default | Required |
|----------|---------|----------|
| `OPENCODE_API_KEY` | — | Yes (falls back to `OPENAI_API_KEY`) |
| `OPENCODE_BASE_URL` | `https://opencode.ai/zen/v1` | No |
| `LLM_MODEL_NAME` | `deepseek-v4-flash-free` | No |
| `TRIAGE_DB_PATH` | `./data/triage.db` | No (persistent volume in prod) |

---

## Project structure

```
log-triage-assistant/
├── src/
│   ├── api.py                    # FastAPI app + endpoints (serves SPA too)
│   ├── classifier.py             # LLM-based classifier
│   ├── db.py                     # SQLite storage layer
│   ├── parser.py                 # Log text parser / error line extractor
│   └── prompts.py                # LLM prompt templates
├── web/                          # Frontend (vanilla SPA)
│   ├── index.html                # App shell + screen templates
│   ├── styles.css                # Design tokens, dark theme
│   └── app.js                    # Hash router + API calls + charts
├── data/
│   ├── __init__.py
│   ├── sample_logs.py            # 45 sample logs (single source of truth)
│   └── triage.db                 # SQLite DB (auto-created, gitignored)
├── tests/
│   ├── test_api.py               # API endpoint tests
│   ├── test_classifier.py        # Classifier logic tests
│   ├── test_db.py                # Storage layer tests
│   ├── test_integration.py       # End-to-end pipeline tests
│   ├── test_live_llm.py          # Live LLM tests (excluded by default)
│   ├── test_parser.py            # Parser unit tests
│   ├── test_prompts.py           # Prompt template tests
│   └── test_sample_data.py       # Sample log data integrity tests
├── streamlit_app.py              # Deprecated Streamlit entry point (alternative UI)
├── app_pages/                    # Deprecated Streamlit pages
├── docs/
│   ├── architecture.md           # Data flow + endpoints
│   ├── business-logic.md         # Error taxonomy + decision flowchart
│   ├── patterns.md               # Coding rules
│   └── tech-stack.md             # Stack summary
├── Sample_Logs_Titles.xlsx       # Original log data (Excel reference)
├── Yash-Solanki-Application-Support-Engineer.pdf  # Resume
├── requirements.txt              # Python dependencies
├── pytest.ini                    # Pytest config
├── Procfile                      # Railway process definition
├── railway.json                  # Railway deploy config
├── .env.example                  # Env var template
├── SPECS.md                      # Build specs and test status
├── AGENTS.md                     # AI agent instructions
└── PROJECT.md                    # This file
```

---

## Frontend details (for AI handoff)

### Current UI — page by page

Single-page app in `web/`. `app.js` does hash-based client routing
(`#/triage`, `#/history`, `#/dashboard`) and re-renders the matching
view into `#main`. Templates live in `index.html`.

#### 1. Triage (`#/triage`)
- Textarea for raw log text with live char count
- Buttons: Load sample, Browse All Samples, Clear, Classify
- Submits `POST /triage`, renders a result card (category badge, animated
  confidence gauge, extracted error line, root cause summary, suggested
  action, optional "why unclassified" block, expandable raw log)

#### 2. History (`#/history`)
- Category filter chips (All + the 5 categories) + Refresh
- Fetches `GET /history`, renders compact list; click to expand a result card

#### 3. Dashboard (`#/dashboard`)
- Fetches `GET /stats`; renders 4 stat cards, SVG category donut, 14-day trend bars

### Theme (web/styles.css design tokens)

| Token | Value | Usage |
|-------|-------|-------|
| `--accent` | `#3B82F6` | Primary actions, active elements |
| `--bg` | `#0A0D12` | Page background |
| `--panel` | `#12161D` | Cards, panels |
| `--text-primary` | `#E6EDF3` | Body text |
| `--border` | `#2A3140` | Borders, dividers |
| `--info` | `#58A6FF` | High confidence, links |
| `--danger` | `#F85149` | Errors, provisioning-fault |
| Category vars | `--cat-next-tache`, `--cat-state-transition`, `--cat-provisioning`, `--cat-api`, `--cat-unclassified` | Badge/chart colors |

### Font stack

- **Body/Headings:** Space Grotesk (Google Fonts)
- **UI text:** Inter
- **Code:** JetBrains Mono
- Loaded via Google Fonts `<link>` in `web/index.html`

### Improvement opportunities (not shipped — out of current scope)

These are concrete gaps a future iteration could address:
batch upload, CSV/JSON export, light/dark toggle, keyboard shortcuts,
SSE streaming, side-by-side comparison.

### API contract

```
POST /triage
Content-Type: application/json

Request:
{
  "log_text": "string — raw log entry"
}

Response (200):
{
  "id": int,
  "created_at": "ISO timestamp",
  "raw_text": "string",
  "extracted_error_line": "string",
  "category": "next-tache-error | state-transition-block | provisioning-fault | api-integration-error | unclassified",
  "root_cause_summary": "string — plain English explanation",
  "confidence": 85,                    // 0-100 integer
  "suggested_action": "string — what to do next",
  "unclassified_reason": "string | null"  // only when category=unclassified
}

Error (422): Validation error
Error (500/502): Classifier runtime error / missing API key
```

### How to run locally

```bash
cd log-triage-assistant
pip install -r requirements.txt
set OPENCODE_API_KEY=your_key_here     # Windows
# export OPENCODE_API_KEY=your_key_here   # macOS/Linux
uvicorn src.api:app --port 8000
```

Open http://localhost:8000 — the SPA is served from the same process.

### How to run tests

```bash
cd log-triage-assistant
python -m pytest tests/ -q
```

### How to deploy (Railway)

1. Push the repo to GitHub.
2. On Railway, create a new project → Deploy from GitHub repo.
3. Add env vars: `OPENCODE_API_KEY` (required); optionally
   `OPENCODE_BASE_URL`, `LLM_MODEL_NAME`.
4. Optional but recommended: mount a volume and set
   `TRIAGE_DB_PATH=/data/triage.db` so history survives restarts.
5. Railway uses `Procfile`/`railway.json` automatically (start command
   `uvicorn src.api:app --host 0.0.0.0 --port $PORT`, health check `/health`).

---

## Sample logs

45 logs in `data/sample_logs.py`, sourced from:
- Real telecom OSS/BSS error patterns (ISAP, OFM, CDOT, Huawei)
- Scenarios from Yash Solanki's resume (BSNL 100M+ subscriber deployment)
- Azure AD / M365 integration issues

Each log has: `title`, `category`, `tag`, `log` (raw text).

To add logs: edit `data/sample_logs.py`, add to the `SAMPLE_LOGS` list.

---

## Code conventions

- One function, one responsibility
- No silent fallback — `unclassified` is a valid output, not an error
- All LLM prompts in `src/prompts.py` (not inline)
- SPA: SVG icons, no emojis; sentence casing for titles/labels
- `pre`/`code` blocks for log display (select-and-copy friendly)

---

## Git info

- **Current branch:** `fix/swap-llm-provider`
- **Remote:** `origin` → `https://github.com/yashsolanki27/log-triage-assistant.git`
