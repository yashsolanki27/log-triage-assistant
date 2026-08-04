# SPECS.md — Log Triage Assistant v1

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

- [x] Unit 4: API — src/api.py
      FastAPI POST /triage, body: {log_text: str}
      Calls parser → classifier, returns JSON result.

- [ ] Unit 5: UI — streamlit_app.py
      Textbox for log paste, submit button, calls API, displays result fields.

## Build order note (Tip 14)

Not list order. Build order: Unit 2 (prompt) → Unit 1 (parser) → Unit 3 (classifier,
depends on both) → Unit 4 (API) → Unit 5 (UI, depends on API).

## TESTS

- [x] Unit 1: parser strips noise, keeps error line — 3 sample logs, known expected extraction
- [x] Unit 2: prompt template renders without missing variables
- [x] Unit 3: classifier — 5 synthetic logs per category (5x5=25 cases) → correct category ≥90%
- [x] Unit 3: low-signal/garbage log → returns unclassified with non-empty reason
- [x] Unit 4: API returns 200 + correct schema on valid input, 422 on empty log_text
- [ ] Unit 5: manual — self-test pass via Chrome DevTools MCP once built (Tip 12)
