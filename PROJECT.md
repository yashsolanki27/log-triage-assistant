# PROJECT.md — OSS/BSS Log Classifier

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
┌─────────────┐     ┌────────────────┐     ┌──────────────┐
│   Parser     │────▶│   Classifier   │────▶│   FastAPI     │
│ src/parser.py│     │src/classifier.py│    │  src/api.py   │
└─────────────┘     └────────────────┘     └──────┬───────┘
                                                   │
                                                   ▼
                                          ┌─────────────────┐
                                          │  Streamlit UI    │
                                          │ streamlit_app.py │
                                          └─────────────────┘
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

4. **API** (`src/api.py`) — FastAPI `POST /triage` endpoint.
   Request: `{log_text: str}` → Response: full classification result.

5. **UI** (`streamlit_app.py` + `app_pages/`) — Streamlit multi-page app.
   Dark OLED theme, two tabs: Analyze logs + Sample logs.

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
| Frontend | Streamlit 1.60+ | Dark OLED theme via `.streamlit/config.toml` |
| Testing | pytest | 75 tests, all passing |
| Storage | None (stateless) | classify-in, result-out |

### Environment variables

| Variable | Default | Required |
|----------|---------|----------|
| `OPENCODE_API_KEY` | — | Yes |
| `OPENCODE_BASE_URL` | `https://opencode.ai/zen/v1` | No |
| `LLM_MODEL_NAME` | `deepseek-v4-flash-free` | No |

---

## Project structure

```
log-triage-assistant/
├── streamlit_app.py              # Entry point — navigation + shared sidebar
├── app_pages/
│   ├── triage.py                 # Analyze logs page (paste → classify → results)
│   └── logs_list.py              # Sample logs page (reads from data/)
├── data/
│   ├── __init__.py
│   └── sample_logs.py            # 39 sample logs (single source of truth)
├── src/
│   ├── __init__.py
│   ├── api.py                    # FastAPI POST /triage
│   ├── classifier.py             # LLM-based classifier
│   ├── parser.py                 # Log text parser / error line extractor
│   └── prompts.py                # LLM prompt templates
├── tests/
│   ├── test_api.py               # API endpoint tests
│   ├── test_classifier.py        # Classifier logic tests (25+ cases)
│   ├── test_integration.py       # End-to-end pipeline tests
│   ├── test_live_llm.py          # Live LLM tests (excluded by default)
│   ├── test_parser.py            # Parser unit tests
│   └── test_prompts.py           # Prompt template tests
├── docs/
│   ├── architecture.md           # Data flow diagram
│   ├── business-logic.md         # Error taxonomy + decision flowchart
│   ├── patterns.md               # Coding rules
│   └── tech-stack.md             # Stack summary
├── .streamlit/
│   └── config.toml               # Dark OLED theme config
├── Sample_Logs_Titles.xlsx       # Original log data (Excel reference)
├── requirements.txt              # Python dependencies
├── pytest.ini                    # Pytest config
├── SPECS.md                      # Build specs and test status
├── AGENTS.md                     # AI agent instructions
└── README.md                     # ← You are here
```

---

## Frontend details (for AI handoff)

### Current UI

The frontend is a **Streamlit multi-page app** with a dark OLED theme.

**Pages:**
1. **Analyze logs** (`app_pages/triage.py`) — Text area for log paste,
   "Classify log" button, results display with category badge, confidence
   score, root cause, suggested action, and unclassified reason.

2. **Sample logs** (`app_pages/logs_list.py`) — 39 pre-built logs grouped
   by category. Each log shows title, original tag, and raw log text in a
   code block. Users select text, copy (Ctrl+C), and paste into the
   Analyze page.

**Theme:** `.streamlit/config.toml` — Dark OLED palette:
- Background: `#0d1117` / `#161b22`
- Primary: `#3B82F6` (blue)
- Text: `#e6edf3`
- Font: Fira Sans + Fira Code
- Rounded corners (10px), visible widget borders

**Navigation:** Top tabs via `st.navigation()` — "Analyze logs" + "Sample logs"

**Sidebar:** Shared across pages — project description, how-it-works,
category reference table, quick start guide.

### What the frontend does NOT have (improvement opportunities)

- No history of past classifications (no session persistence)
- No batch upload (one log at a time)
- No export/download of results
- No charts or analytics dashboard
- No light/dark mode toggle (dark only)
- No mobile-optimized layout
- No loading skeleton (just a spinner)
- No keyboard shortcuts
- No real-time classification streaming
- No authentication or multi-user support

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
  "category": "next-tache-error | state-transition-block | provisioning-fault | api-integration-error | unclassified",
  "root_cause_summary": "string — plain English explanation",
  "confidence": 85,                    // 0-100 integer
  "suggested_action": "string — what to do next",
  "unclassified_reason": "string | null"  // only when category=unclassified
}

Error (422): Validation error
Error (500): Classifier runtime error / missing API key
```

### How to run locally

```bash
# Terminal 1 — Backend
cd log-triage-assistant
pip install -r requirements.txt
export OPENCODE_API_KEY=your_key_here
uvicorn src.api:app --port 8000

# Terminal 2 — Frontend
cd log-triage-assistant
streamlit run streamlit_app.py --server.port 8501
```

Open http://localhost:8501

### How to run tests

```bash
cd log-triage-assistant
python -m pytest tests/ -v
```

---

## Sample logs

39 logs in `data/sample_logs.py`, sourced from:
- Real telecom OSS/BSS error patterns (Zsmart, ISAP, OFM, CDOT, Huawei)
- Scenarios from Yash Solanki's resume (BSNL 100M+ subscriber deployment)
- Azure AD / M365 integration issues

Each log has: `title`, `category`, `tag`, `log` (raw text).

To add logs: edit `data/sample_logs.py`, add to the `SAMPLE_LOGS` list.

---

## Code conventions

- One function, one responsibility
- No silent fallback — `unclassified` is a valid output, not an error
- All LLM prompts in `src/prompts.py` (not inline)
- Material Symbols icons (`:material/icon_name:`) — no emojis
- Sentence casing for titles and labels
- `st.code()` for log display (select-and-copy friendly)

---

## Git info

- **Current branch:** `fix/swap-llm-provider`
- **Remote:** `origin`
- **Status:** Clean working tree after commit
