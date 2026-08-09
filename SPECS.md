# SPECS.md — LogPulse v1

## Units

- [x] Unit 1: Parser — src/parser.py
      Input: raw pasted log text (single entry, possibly multi-line stack/context)
      Output: cleaned {raw_text, extracted_error_line} dict
      No classification logic here — extraction only.

- [x] Unit 2: Prompt template — src/prompts.py
      Holds the classification prompt, referencing docs/business-logic.md taxonomy.
      Not inline in classifier.py (patterns.md rule).

- [x] Unit 3: Classifier — src/classifier.py
      Input: parser output. Calls LLM with prompts.py template.
      Output: {category, root_cause_summary, confidence, suggested_action, unclassified_reason}
      Confidence <70% → force category=unclassified, populate unclassified_reason.
      Enforced in code (_apply_confidence_rule), not just prompted — safety net
      in case the model doesn't self-police.

- [x] Unit 4: API — src/api.py
      FastAPI POST /triage, body: {log_text: str}
      Calls parser → classifier, returns JSON result.
      Extended beyond original spec: GET /history, GET /triage/{id}, GET /stats
      (needed for the History/Dashboard screens — requires src/db.py storage,
      which supersedes the "no storage needed v1" note in tech-stack.md).

- [x] Unit 5: UI — web/ (index.html, styles.css, app.js)
      Built as a vanilla HTML/CSS/JS SPA instead of Streamlit — see README
      "Frontend note" for reasoning. Same core flow (paste → submit → result)
      plus History and Dashboard screens, added per updated scope.

## Build order note (Tip 14)

Not list order. Build order: Unit 2 (prompt) → Unit 1 (parser) → Unit 3 (classifier,
depends on both) → Unit 4 (API) → Unit 5 (UI, depends on API).

## TESTS

- [x] Unit 1: parser strips noise, keeps error line — 3 sample logs, known expected extraction
- [x] Unit 2: prompt template renders without missing variables
- [x] Unit 3: classifier — non-LLM logic covered (confidence-rule enforcement,
      JSON parsing/fence-stripping, invalid-category handling) in
      tests/test_classifier.py. NOT covered: the 25-case LLM accuracy
      benchmark (5 logs x 5 categories) — that needs real API calls against
      curated sample logs and should be run separately, not as part of
      automated CI (cost + nondeterminism).
- [x] Unit 3: low-signal/garbage log → returns unclassified with non-empty reason
      (code-side rule covered in tests/test_classifier.py; real-LLM pass
      remains a manual, opt-in check — run with `pytest -m live`)
- [x] Unit 4: API returns 200 + correct schema on valid input, 422 on empty log_text
      Covered by tests/test_api.py — /triage, /history, /triage/{id}, /stats,
      404 on missing id, /sample-logs, /health, static frontend serving.
- [x] Unit 5: UI — manual — verified all three screens (Triage/History/Dashboard)
      render, submit, filter, and fetch against the API in a smoke test.
      Real-browser + real-LLM pass documented in README "Live test" note.
- [x] Unit 6: Deployment — Procfile + railway.json, /health liveness probe,
      TRIAGE_DB_PATH env override for a persistent volume, .env.example,
      /sample-logs unified on data/sample_logs.py (single source of truth).
