# LogPulse

An AI-powered OSS/BSS log classification tool that automates root cause analysis for telecom application support engineers. Paste a raw log excerpt, get an instant classification with confidence scoring, root cause summary, and suggested next action.

Built with **FastAPI**, **OpenAI-compatible LLM (DeepSeek V4 Flash)**, **SQLite**, and a custom **vanilla HTML/CSS/JS** frontend with a premium dark theme.

---

## Overview

Telecom support engineers spend hours manually reading logs, identifying error patterns, and determining next steps. This tool eliminates that bottleneck — paste a log, get an instant triage result backed by an LLM classification pipeline.

**Target Users:** Telecom / OSS-BSS application support engineers working with order processing, provisioning, and API integration systems (ISAP, OFM, Huawei, Azure AD).

---

## Features

- **LLM-Powered Classification** — Classifies logs against a 5-category error taxonomy using an LLM
- **Multi-Key Failover** — Set `OPENCODE_API_KEY=key1,key2,key3`; blocked or rate-limited keys auto-swap to the next one
- **Confidence Scoring** — Every result includes a confidence percentage with a hard <70% safety threshold
- **Root Cause Analysis** — Plain English explanation of what went wrong
- **Suggested Actions** — Actionable next steps for each classified error
- **Classification History** — Browse, filter, and review all past triages
- **Analytics Dashboard** — Category distribution donut chart, 14-day volume trend, aggregate stats
- **45 Sample Logs** — Real-world OSS/BSS log samples across all 5 categories
- **RESTful API** — Full CRUD endpoints for integration with existing tooling
- **Responsive Dark Theme** — Custom OLED dark theme with Space Grotesk / JetBrains Mono typography

---

## How It Works

```
┌──────────┐     ┌──────────┐     ┌────────────┐     ┌──────────┐
│  User     │────▶│  Parser  │────▶│ Classifier │────▶│  FastAPI │
│  Input    │     │          │     │   (LLM)    │     │  Server  │
└──────────┘     └──────────┘     └────────────┘     └────┬─────┘
                                                           │
                                                ┌──────────┴──────────┐
                                                │                     │
                                                ▼                     ▼
                                        ┌────────────┐       ┌────────────┐
                                        │  Frontend  │       │   SQLite   │
                                        │  (SPA)     │       │   (History)│
                                        └────────────┘       └────────────┘
```

### Pipeline

1. **Parser** (`src/parser.py`) — Extracts the most diagnostic error line from raw multi-line logs using a regex priority system (exception classes > ERROR/FATAL markers > error keywords > first non-empty line)

2. **Prompt Template** (`src/prompts.py`) — Renders a structured classification prompt referencing the error taxonomy, requesting JSON output with category, confidence, root cause, and action

3. **Classifier** (`src/classifier.py`) — Calls the LLM via OpenAI-compatible API, parses the JSON response, enforces the 70% confidence safety threshold, and validates category output

4. **API** (`src/api.py`) — FastAPI server exposing endpoints for triage, history, dashboard stats, and serving the frontend SPA

5. **Frontend** (`web/`) — Vanilla SPA with hash-based client-side routing across Triage, History, and Dashboard screens

---

## Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Language | Python | 3.11+ |
| Backend Framework | FastAPI | >= 0.115 |
| ASGI Server | Uvicorn | >= 0.30 |
| LLM Integration | OpenAI SDK | >= 1.0 |
| LLM Provider | OpenCode Zen (DeepSeek V4 Flash Free) | — |
| Data Validation | Pydantic | >= 2.8 |
| Database | SQLite3 | stdlib |
| Frontend | Vanilla HTML / CSS / JavaScript | ES6+ |
| HTTP Client | httpx (test client) | >= 0.27 |
| Testing | pytest | >= 8.0 |
| Fonts | Google Fonts — Space Grotesk, Inter, JetBrains Mono | — |

---

## Error Categories

| Category | Label | Description |
|----------|-------|-------------|
| `next-tache-error` | Task sequencing | Task started before prerequisite completed |
| `state-transition-block` | Stuck order | Order/subscriber stuck in a state (masterless, collab-wait failure) |
| `provisioning-fault` | Config / node failure | DSLAM / LMG / BNG / OLT provisioning rejected |
| `api-integration-error` | API failure | REST / SOAP integration failed (ISAP / OFM style) |
| `unclassified` | Needs review | No confident match — flagged for human review (confidence < 70%) |

---

## Screens

### 1. Triage
Paste a raw log entry, click "Classify", and instantly see the detected category (with animated confidence gauge), root cause summary, suggested action, and unclassified reason (if applicable). Supports loading sample logs for quick testing.

### 2. History
Browse every past triage result. Filter by category. Click any entry to expand the full classification card with all details.

### 3. Dashboard
Visual overview with total triaged count, unclassified rate, top category, category distribution donut chart (SVG), and 14-day volume trend bar chart.

---

## Project Structure

```
log-triage-assistant/
├── src/                        # Backend source code
│   ├── api.py                  # FastAPI application + endpoints
│   ├── classifier.py           # LLM classification logic
│   ├── db.py                   # SQLite storage layer
│   ├── parser.py               # Log text parser / error line extractor
│   └── prompts.py              # LLM prompt templates
│
├── web/                        # Frontend (vanilla SPA)
│   ├── index.html              # Single-page app HTML + templates
│   ├── styles.css              # Custom CSS (design tokens, dark theme)
│   └── app.js                  # Client-side router + API calls + charts
│
├── streamlit_app.py            # Deprecated Streamlit entry (alternative UI)
├── app_pages/                  # Deprecated Streamlit pages
│
├── data/
│   ├── sample_logs.py          # 45 real-world OSS/BSS sample logs
│   └── triage.db               # SQLite database (auto-created, gitignored)
│
├── docs/                       # Project documentation
│   ├── architecture.md         # Data flow diagram
│   ├── business-logic.md       # Error taxonomy + confidence rule
│   ├── patterns.md             # Coding conventions
│   └── tech-stack.md           # Stack summary
│
├── tests/                      # Test suite (70 unit + 12 live, opt-in)
│   ├── test_api.py             # API endpoint tests
│   ├── test_classifier.py      # Classifier logic tests
│   ├── test_db.py              # Storage layer tests
│   ├── test_integration.py     # Full pipeline integration tests
│   ├── test_parser.py          # Parser unit tests
│   ├── test_prompts.py         # Prompt template tests
│   ├── test_sample_data.py     # Sample log data integrity tests
│   └── test_live_llm.py        # Live LLM tests (excluded by default)
│
├── Procfile                    # Railway process definition
├── railway.json                # Railway deploy config
├── .env.example                # Environment variable template
├── requirements.txt            # Python dependencies
├── pytest.ini                  # Pytest configuration
├── PROJECT.md                  # Full project specification
├── SPECS.md                    # Build units checklist
└── AGENTS.md                   # AI agent instructions
```

---

## Getting Started

### Prerequisites

- Python 3.11 or higher
- pip
- An LLM API key (OpenCode Zen / OpenAI compatible)

### Installation

```bash
# Clone the repository
git clone https://github.com/yashsolanki27/log-triage-assistant.git
cd log-triage-assistant

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

### Environment Variables

```bash
# Copy the example env file
cp .env.example .env

# Edit .env and add your API key
OPENCODE_API_KEY=your_api_key_here
# For automatic failover, add multiple comma-separated keys:
# OPENCODE_API_KEY=key1,key2,key3
```

| Variable | Default | Required |
|----------|---------|----------|
| `OPENCODE_API_KEY` | — | Yes (falls back to `OPENAI_API_KEY`) |
| `OPENCODE_BASE_URL` | `https://opencode.ai/zen/v1` | No |
| `LLM_MODEL_NAME` | `deepseek-v4-flash-free` | No |
| `TRIAGE_DB_PATH` | `./data/triage.db` | No |

---

## Running the App

### Primary Mode (Vanilla SPA — Recommended)

```bash
# Start the FastAPI server (serves both API + frontend)
uvicorn src.api:app --reload
```

Open **http://localhost:8000** — the frontend is served from the same process.

### Alternative Mode (Streamlit UI — deprecated)

```bash
# Terminal 1 — Backend
uvicorn src.api:app --port 8000

# Terminal 2 — Streamlit Frontend
streamlit run streamlit_app.py --server.port 8501
```

Open **http://localhost:8501**

### Deploy to Railway

The repo ships with `Procfile` and `railway.json`:

1. Push to GitHub, then create a Railway project from the repo.
2. Set env vars: `OPENCODE_API_KEY` (required), optionally
   `OPENCODE_BASE_URL` and `LLM_MODEL_NAME`.
3. Recommended: attach a volume and set `TRIAGE_DB_PATH=/data/triage.db`
   so triage history survives restarts.
4. Railway auto-detects the start command
   (`uvicorn src.api:app --host 0.0.0.0 --port $PORT`) and uses `/health`
   as the liveness check.

---

## Running Tests

```bash
# Run all tests (excluding live LLM tests)
pytest tests/ -q

# Run with verbose output
pytest tests/ -v

# Include live LLM tests (requires valid API key)
pytest tests/ -m "live" -v
```

---

## API Reference

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/triage` | Classify a log entry |
| `GET` | `/history` | List past triages (filterable, paginated) |
| `GET` | `/triage/{id}` | Get a single triage by ID |
| `GET` | `/stats` | Dashboard aggregate statistics |
| `GET` | `/health` | Health check |

### POST /triage

**Request:**
```json
{
  "log_text": "2024-01-15 10:23:45 ERROR [TaskExecutor] NullPointerException at com.order.NextTaskValidator.validate(NextTaskValidator.java:142)"
}
```

**Response (200):**
```json
{
  "category": "next-tache-error",
  "root_cause_summary": "A NullPointerException occurred in the NextTaskValidator, indicating a task was started before its prerequisite completed successfully.",
  "confidence": 85,
  "suggested_action": "Check the task dependency chain in the order management system and ensure all prerequisite tasks are marked complete before triggering the next task.",
  "unclassified_reason": null
}
```

**Error Responses:**
- `422` — Validation error (missing or invalid `log_text`)
- `500` — Classifier runtime error or missing API key

### GET /history?category=next-tache-error&limit=20&offset=0

Returns a paginated list of past triage results, optionally filtered by category.

### GET /stats

Returns aggregate statistics including total triaged count, unclassified rate, top category, per-category breakdown, and 14-day volume trend.

---

## Architecture Decisions

- **Vanilla JS over Streamlit (Primary UI):** The brief required a premium dark theme with fine-grained responsive control, custom animated gauges, and SVG charts — straightforward in hand-written CSS/JS and awkward inside Streamlit's component model.
- **70% Confidence Threshold:** Enforced in code as a hard safety net, not just prompted. Below 70% forces the category to `unclassified`.
- **No Silent Fallback:** `unclassified` is a valid output. Malformed LLM responses raise `RuntimeError` (surfaced as HTTP 502), never silently guessed.
- **Prompt Isolation:** All LLM prompts live in `src/prompts.py`, never inline in the classifier.
- **SQLite for History (v1.1):** Added post-v1 to support History and Dashboard screens. Originally spec'd as stateless.

---

## Sample Logs

45 real-world OSS/BSS log samples in `data/sample_logs.py`, sourced from:
- Telecom systems: ISAP, OFM, CDOT, Huawei
- Azure AD / Microsoft 365 integration issues
- Scenarios from BSNL 100M+ subscriber deployment

Each log entry includes: `title`, `category`, `tag`, and raw `log` text.

---

## Development

### Code Conventions

- One function, one responsibility
- No silent fallback — `unclassified` is valid output, not an error
- All LLM prompts in `src/prompts.py`
- Material Symbols icons (`:material/icon_name:`) — no emojis
- Sentence casing for titles and labels
- `st.code()` for log display (select-and-copy friendly)

### Documentation

| File | Purpose |
|------|---------|
| `PROJECT.md` | Full project specification with API contract |
| `SPECS.md` | Build units checklist and test status |
| `AGENTS.md` | AI agent instructions and routing table |
| `docs/architecture.md` | Data flow diagram |
| `docs/business-logic.md` | Error taxonomy and decision rules |
| `docs/patterns.md` | Coding conventions |
| `docs/tech-stack.md` | Technology stack summary |

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit changes (`git commit -m "Add your feature"`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Open a Pull Request

---

## Author

**Yash Solanki** — Application Support Engineer

- GitHub: [yashsolanki27](https://github.com/yashsolanki27)
- Resume: `Yash-Solanki-Application-Support-Engineer.pdf`

---

## License

This project is for educational and portfolio purposes.
