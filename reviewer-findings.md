# Reviewer Findings

Reviewed: `src/parser.py`, `src/classifier.py`, `src/api.py`
Against: `docs/patterns.md`, `docs/business-logic.md`
Date: 2026-08-04

---

## Fixed (4 findings — see commit)

### Finding 5: Missing `unclassified_reason` validation (classifier.py)
- **Was:** `_validate_output` never checked that `unclassified_reason` is a non-empty string when category is `"unclassified"`.
- **Fix:** Added validation in `_validate_output` — raises `RuntimeError` if category is `unclassified` and reason is missing or empty.
- **Regression tests:** `test_unclassified_with_empty_reason_raises`, `test_unclassified_with_none_reason_raises`, `test_unclassified_with_valid_reason_passes`.

### Finding 7: Hardcoded model name (classifier.py)
- **Was:** Model name `"deepseek-v4-flash-free"` hardcoded on line 79.
- **Fix:** Extracted to `MODEL_NAME` constant, overridable via `LLM_MODEL_NAME` env var.
- **Regression tests:** Existing test suite passes; model is now configurable without code change.

### Finding 8: Missing JSON-fence stripping (classifier.py)
- **Was:** `_parse_response` called `json.loads(raw_response)` directly. LLMs often wrap JSON in ` ```json ... ``` ` fences, causing `RuntimeError`.
- **Fix:** `_parse_response` now strips markdown code fences before parsing.
- **Regression tests:** `test_parse_response_strips_json_fences`, `test_parse_response_strips_plain_fences`, `test_parse_response_plain_json_still_works`, `test_parse_response_bare_fences_still_invalid`.

### Finding 10: Unhandled `RuntimeError` from classifier (api.py)
- **Was:** `triage` caught `ValueError` from parser but let `RuntimeError` from classifier propagate as opaque HTTP 500.
- **Fix:** Added `except RuntimeError` block that returns `500` with structured `detail` message.
- **Regression tests:** `test_triage_classifier_runtime_error_returns_500`, `test_triage_classifier_missing_api_key_returns_500`, `test_triage_classifier_invalid_category_returns_500`.

---

## Remaining findings → `tech-debt-tracker.md`

Findings 1–4, 6, 9, 11–15 moved to `tech-debt-tracker.md` (11 items).
