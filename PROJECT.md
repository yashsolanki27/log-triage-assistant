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
├── Yash-Solanki-Application-Support-Engineer.pdf  # Resume
├── ui-ux-pro-max/                # External UI/UX design system tool
├── requirements.txt              # Python dependencies
├── pytest.ini                    # Pytest config
├── SPECS.md                      # Build specs and test status
├── AGENTS.md                     # AI agent instructions
└── PROJECT.md                    # This file
```

---

## Frontend details (for AI handoff)

### Current UI — page by page

#### 1. `streamlit_app.py` (entry point)

- Calls `st.set_page_config()` — title "OSS/BSS Log Classifier", icon
  `:material/psychology:`, layout "wide"
- Defines `st.navigation()` with two pages (top tabs):
  - "Analyze logs" → `app_pages/triage.py`
  - "Sample logs" → `app_pages/logs_list.py`
- Renders shared sidebar:
  - Project title + caption
  - "How it works" (4-step numbered list)
  - "Error categories" table (5 rows)
  - "Quick start" tip
  - Backend info caption

#### 2. `app_pages/triage.py` (analyze page)

Layout (top to bottom):
1. Section header: "Paste your log entry" + caption
2. `st.container(border=True)` containing:
   - `st.text_area` — 200px height, placeholder with example log
   - `st.columns([6, 1])` — spacer + "Classify log" button (primary, `:material/search:`)
3. On click → `requests.post("http://localhost:8000/triage", json={"log_text": ...})`
4. Results (when successful):
   - `st.success("Classification complete")`
   - 3-column metrics row:
     - "Detected category" → `st.badge(category, color=...)`
     - "Confidence score" → `st.badge(f"{confidence}%", color=green/orange/red)`
     - "Verdict" → `st.badge("Classified" or "Needs manual review")`
   - Two bordered containers:
     - "Root cause" → `st.markdown(result["root_cause_summary"])`
     - "Suggested next action" → `st.markdown(result["suggested_action"])`
   - Conditional bordered container:
     - "Why it is unclassified" → only when `unclassified_reason` is not null
5. Error states: `st.error()` for connection, timeout, HTTP errors
6. Empty input: `st.warning("Paste a log entry first")`

#### 3. `app_pages/logs_list.py` (sample logs page)

Layout (top to bottom):
1. Section header: "Sample logs for testing" + copy instructions
2. For each category (next-tache-error → unclassified):
   - Category heading with badge count: `#### Task sequencing :gray-badge[2 logs]`
   - Caption: category description
   - For each log in that category:
     - `st.container(border=True)` with `st.columns([4, 6])`:
       - Left: bold title + caption with tag
       - Right: `st.code(entry["log"], language=None, wrap_lines=True)`
3. Footer: `st.info("Switch to Analyze logs tab...")`

### Theme colors (`.streamlit/config.toml`)

| Token | Hex | Usage |
|-------|-----|-------|
| Primary | `#3B82F6` | Buttons, active elements, links |
| Background | `#0d1117` | Main page background |
| Secondary BG | `#161b22` | Widget backgrounds, code blocks |
| Text | `#e6edf3` | Body text |
| Border | `#30363d` | Widget borders, containers |
| Code text | `#d2a8ff` | Inline code, code blocks |
| Red | `#f85149` | Errors, provisioning-fault |
| Green | `#3fb950` | Success, high confidence |
| Orange | `#d29922` | Warnings, medium confidence |
| Blue | `#58a6ff` | Links, next-tache-error |
| Violet | `#bc8cff` | api-integration-error |
| Gray | `#8b949e` | Unclassified, muted text |

### Font stack

- **Body:** Fira Sans (Google Fonts) — weights 300-700
- **Headings:** Fira Sans — weights 500-700
- **Code:** Fira Code (Google Fonts) — weights 400-600
- **Base size:** 15px

### What the frontend does NOT have (improvement opportunities)

These are concrete gaps the next AI should address:

1. **No classification history** — Results disappear on page refresh.
   Add `st.session_state` to persist past results in a scrollable list.

2. **No batch upload** — One log at a time. Add file upload (`.txt`, `.log`)
   that processes multiple logs and shows results in a table.

3. **No export/download** — Results can't be saved. Add CSV/JSON export button.

4. **No analytics dashboard** — No charts showing classification distribution,
   confidence trends, or category breakdown over time.

5. **No light/dark mode toggle** — Dark only. Could add `[theme.light]` and
   `[theme.dark]` sections to config.toml and let users switch.

6. **No mobile optimization** — Layout is "wide" but not responsive. Code blocks
   overflow on small screens.

7. **No loading skeleton** — Just a spinner. Add skeleton placeholders for
   better perceived performance.

8. **No keyboard shortcuts** — No Ctrl+Enter to submit, no tab navigation.

9. **No real-time streaming** — LLM response comes all at once. Could use
   Server-Sent Events to stream the classification as it's generated.

10. **No side-by-side comparison** — Can't compare two log classifications.

11. **No search/filter in sample logs** — 39 logs with no search. Add a
    `st.text_input` filter above the log list.

12. **No category color coding on results** — Category badge is colored but
    the result containers are all the same. Could tint containers by category.

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
- Prefer `st.container(border=True)` over `st.divider()` for spacing
- Use `st.badge()` for status indicators
- Never use `use_container_width` (deprecated) — use `width="stretch"` instead

---

## Git info

- **Current branch:** `fix/swap-llm-provider`
- **Remote:** `origin` → `https://github.com/yashsolanki27/log-triage-assistant.git`
- **Status:** Clean working tree after commit
