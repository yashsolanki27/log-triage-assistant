# Architecture

log file/text → parser (extract error line + context)
→ classifier (LLM call, business-logic.md taxonomy)
→ FastAPI endpoint returns {category, root_cause_summary, confidence}
→ Streamlit UI displays result

Parser logic: src/parser.py
Classifier logic: src/classifier.py
API layer: src/api.py — FastAPI POST /triage, body {log_text: str}, returns {category, root_cause_summary, confidence, suggested_action, unclassified_reason}
UI layer: streamlit_app.py — Text input for log paste, submit button, calls API, displays classification result
