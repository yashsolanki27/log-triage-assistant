# Reviewer Findings

Reviewed: `src/parser.py`, `src/classifier.py`, `src/api.py`, `src/db.py`
Against: `docs/patterns.md`, `docs/business-logic.md`
Date: 2026-08-08 (latest update)

---

## Fixed (7 findings)

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

### Finding 16: Missing `/sample-logs` endpoint (api.py)
- **Was:** No endpoint to serve sample logs from `Sample_Logs_Titles.xlsx`.
- **Fix:** Added `GET /sample-logs` endpoint that reads all 40 logs from the Excel file via openpyxl.
- **Regression tests:** `test_sample_logs_returns_list`, `test_sample_logs_has_all_entries`, `test_sample_logs_entries_have_valid_fields`.
- **Later change (supersedes this fix):** `/sample-logs` now reads from
  `data/sample_logs.py` (documented single source of truth) instead of the
  Excel file, so `openpyxl` was removed from `requirements.txt`. The tests
  were updated to compare against `data.sample_logs.SAMPLE_LOGS`.

### Finding 17: Missing `openpyxl` dependency (requirements.txt)
- **Was:** `openpyxl` was used by the `/sample-logs` endpoint but not listed in `requirements.txt`.
- **Fix:** Added `openpyxl>=3.1` to `requirements.txt`.
- **Later change:** `openpyxl` removed again once `/sample-logs` switched to `data/sample_logs.py`.

### Finding 18: Dead code `_row_to_dict` (db.py)
- **Was:** `_row_to_dict` function existed but was never called anywhere.
- **Fix:** Removed the unused function.

---

## New Test Coverage Added

### `tests/test_db.py` — 14 tests (NEW file)
Direct unit tests for the SQLite storage layer:
- `test_init_db_no_error` — DB initialization
- `test_save_triage_returns_correct_shape` — save returns proper dict
- `test_save_triage_increments_id` — IDs auto-increment
- `test_get_triage_returns_saved` — fetch by ID
- `test_get_triage_returns_none_for_missing` — missing ID returns None
- `test_list_triages_returns_all` — list all entries
- `test_list_triages_respects_limit` — pagination limit
- `test_list_triages_respects_offset` — pagination offset
- `test_list_triages_filters_by_category` — category filter
- `test_list_triages_empty` — empty DB returns []
- `test_get_stats_empty_db` — stats on empty DB
- `test_get_stats_with_data` — stats with data
- `test_get_stats_trend_sorted_by_day` — trend sorting
- `test_save_triage_with_unclassified_reason` — unclassified reason storage

### `tests/test_sample_data.py` — 12 tests (NEW file + expanded)
Data integrity validation for `data/sample_logs.py`:
- `test_categories_match_classifier_taxonomy` — taxonomy consistency
- `test_sample_logs_is_non_empty_list` — non-empty
- `test_every_entry_has_required_keys` — schema validation
- `test_every_entry_has_non_empty_title` — no empty titles
- `test_every_entry_has_non_empty_log` — no empty logs
- `test_every_category_is_valid` — valid categories
- `test_all_four_error_categories_represented` — all categories present
- `test_no_duplicate_titles` — no duplicates
- `test_minimum_log_length` — minimum 20 chars
- `test_each_error_category_has_minimum_samples` — >= 5 per error category (keeps the 5x5 live benchmark runnable)
- `test_unclassified_has_benchmark_samples` — unclassified >= 5
- `test_tag_implies_consistent_category` — a tag never maps to contradicting categories

### `tests/test_api.py` — 3 new tests added
- `test_sample_logs_returns_list` — endpoint returns list
- `test_sample_logs_has_all_entries` — returns all 40 logs
- `test_sample_logs_entries_have_valid_fields` — field validation

---

## Test Suite Summary

| File | Tests | Status |
|------|-------|--------|
| `test_parser.py` | 10 | All pass |
| `test_prompts.py` | 6 | All pass |
| `test_classifier.py` | 16 | All pass |
| `test_api.py` | 14 | All pass |
| `test_db.py` | 14 | All pass |
| `test_integration.py` | 2 | All pass |
| `test_sample_data.py` | 12 | All pass |
| **Total** | **74** | **All pass** |

10 live LLM tests excluded by default (requires `OPENCODE_API_KEY`),
run separately with `pytest -m live` — verified passing 2026-08-09.

---

## Latest finding (2026-08-09)

### Finding 19: `unclassified_reason` could be null on unclassified results
- **Was:** `_apply_confidence_rule` only guaranteed a non-empty reason when
  confidence was below 70%. An LLM reply of `category=unclassified` with a
  null reason (high confidence) was stored without any explanation —
  contradicting patterns.md ("unclassified is a valid output, never a
  silently hidden one").
- **Fix:** `_apply_confidence_rule` now always ensures a non-empty
  `unclassified_reason` for unclassified results, and prepends the
  below-threshold note whenever a low-confidence reason is present.
- **Regression tests:** `test_confidence_rule_unclassified_with_null_reason_gets_default`
  (new); `test_confidence_rule_preserves_existing_unclassified_reason`
  updated to assert the threshold note is included.

---

## Remaining findings → `tech-debt-tracker.md`

Findings 1–4, 6, 9, 11–15 moved to `tech-debt-tracker.md` (11 items).
