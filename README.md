# Log Triage Assistant

Paste an OSS/BSS log excerpt, get it classified against a root-cause taxonomy
with a confidence score and a suggested next action. Includes a History
screen and a Dashboard for volume/category trends.

## What's here

- `src/parser.py` — extracts the primary error line from raw log text (Unit 1)
- `src/prompts.py` — the classification prompt template (Unit 2)
- `src/classifier.py` — calls the Claude API, enforces the <70% confidence
  → `unclassified` rule as a hard safety net (Unit 3)
- `src/db.py` — SQLite storage for history/dashboard (v1.1 addition — v1 was
  spec'd stateless; see `docs/architecture.md`)
- `src/api.py` — FastAPI app: `/triage`, `/history`, `/triage/{id}`, `/stats`,
  and serves the frontend from `web/` (Unit 4)
- `web/` — the frontend: `index.html`, `styles.css`, `app.js` (Unit 5, built
  as a vanilla single-page app instead of Streamlit — see note below)

## Run it

```bash
pip install -r requirements.txt
cp .env.example .env   # then fill in ANTHROPIC_API_KEY
export $(cat .env | xargs)   # or use a tool like python-dotenv / direnv
uvicorn src.api:app --reload
```

Open http://localhost:8000 — the frontend is served from the same process.

## Run tests

```bash
pytest tests/ -q
```

## Frontend note

`docs/tech-stack.md` originally specced Streamlit for the UI. This build
uses a vanilla HTML/CSS/JS single-page app instead, calling the FastAPI
endpoints via `fetch`. Reasoning: the brief asked for a premium, custom dark
theme with fine-grained responsive control (breakpoints, touch targets,
custom charts/gauges) — that's straightforward in hand-written CSS/JS and
awkward to achieve inside Streamlit's component model. Functionally it's a
drop-in replacement for the specced Unit 5 (same textbox → submit → result
flow), plus History and Dashboard screens added at the user's request.

## Screens

1. **Triage** — paste a log, classify it, see category + confidence gauge +
   root cause summary + suggested action (+ reason, if unclassified).
2. **History** — every past triage, filterable by category, expandable for
   the full result.
3. **Dashboard** — total triaged, unclassified rate, top category, category
   mix (donut), and a 14-day volume trend.

## Known limitation

`src/classifier.py` calls the Anthropic API directly and expects a valid
JSON object back per the schema in `src/prompts.py`. If the model ever
returns malformed JSON or an unrecognised category, the classifier raises
(surfaced as a 502 from `/triage`) rather than silently guessing — per
`docs/patterns.md`, unclassified is a valid output, but a parsing failure is
a real error and should not be hidden as one.
