# Tech Debt Tracker

Migrated from `reviewer-findings.md` on 2026-08-04 (findings 1-4, 6, 9,
11-15 — 11 items). Re-derived against current code on 2026-08-09 after the
v2.0 rewrite (several Part 4b fixes were lost in that rewrite and are marked
as reopened below).

---

## src/parser.py

1. ~~**Silent fallback (patterns.md violation)**~~ — CLOSED: `_extract_error_line` now returns `(line, is_fallback)` and `parse_log` exposes `is_fallback` (True only for Priority 4 fallback), so callers can distinguish a confident extraction from a guess (src/parser.py). Regression fence: `test_parse_returns_is_fallback_*` in tests/test_parser.py.

2. ~~**No handling of binary/garbled input**~~ — CLOSED: `parse_log` now rejects NUL bytes (`\x00`) with a `ValueError` (422 at the API), and the UTF-8 encoding assumption is documented in `parse_log`'s docstring and docs/tech-stack.md ("Input assumptions"). Regression tests `test_nul_bytes_raises` and `test_nul_bytes_only_raises` restored as a fence.

3. ~~**Regex does not cover .NET-style `FaultException`**~~ — CLOSED: the Priority 1 regex `\b\w+(Exception|Error)\b` already matches `FaultException<Detail>`; `\w+` backtracks so `(Exception|Error)` matches `Exception`, and `\b` holds before `<`. Not debt. Regression test `test_parse_dotnet_fault_exception` was lost in the v2.0 rewrite — worth restoring as a fence.

---

## src/classifier.py

4. ~~**Docstring claims `OPENCODE_API_KEY` is used**~~ — CLOSED: `_get_api_keys` now states it reads the `OPENCODE_API_KEY` environment variable (comma-separated keys allowed, `OPENAI_API_KEY` fallback). Not debt.

5. ~~**`_apply_confidence_rule` mutates in-place and returns**~~ — CLOSED: the
   function now copies the input (`dict(result)`) and returns a new dict, never
   mutating the caller's data (src/classifier.py). Code-style rule added to
   docs/patterns.md; regression tests `test_confidence_rule_does_not_mutate_input`
   and `test_confidence_rule_returns_new_dict` restored as a fence.

6. ~~**`base_url` points to `opencode.ai/zen/v1`**~~ — CLOSED: now configurable via `OPENCODE_BASE_URL` env var and documented in docs/tech-stack.md. Not debt.

7. ~~**No request timeout or rate limiting**~~ — CLOSED: the LLM client is built with `timeout=` from `LLM_TIMEOUT` (src/classifier.py `_build_client`), and `POST /triage` is capped at 10 requests/minute per client IP via slowapi (src/api.py `limiter`, dependency in requirements.txt). Bursts return HTTP 429 instead of exhausting the LLM quota. Regression fence: `test_triage_rate_limit_infrastructure` in tests/test_api.py.

8. ~~**`TriageResult.unclassified_reason` typed `str | None` with no conditional constraint**~~ — CLOSED: re-added the `model_validator` on `TriageResult` (src/api.py) dropped by the v2.0 rewrite — `unclassified` requires a non-empty reason, every other category requires `None`. Regression tests `test_triage_result_unclassified_requires_non_empty_reason`, `test_triage_result_unclassified_with_reason_ok`, `test_triage_result_non_unclassified_must_have_none_reason`, `test_triage_result_non_unclassified_with_none_reason_ok`, `test_triage_api_unclassified_with_reason_ok`, and `test_triage_api_rejects_unclassified_without_reason` restored as a fence. Contract documented in docs/business-logic.md ("unclassified_reason contract") and docs/architecture.md.

---

## Cross-cutting / Documentation

9. ~~**`docs/business-logic.md` category descriptions are terse**~~ — CLOSED: each
   category in docs/business-logic.md now carries signal keywords, distinguishing
   features, and real example log lines drawn from data/sample_logs.py; the same
   expanded taxonomy is mirrored into the classification prompt (src/prompts.py).
   Regression tests `test_prompt_taxonomy_has_signal_keywords_for_every_category`,
   `test_prompt_taxonomy_has_example_log_line_for_every_category`, and
   `test_business_logic_doc_mirrors_prompt_taxonomy` restored/added as a fence.

10. ~~**No integration test with real LLM**~~ — CLOSED: `tests/test_live_llm.py` (10 tests, `-m live`) now exercises the real OpenAI-compatible endpoint; excluded from default CI by design. Not debt.

11. ~~**`_call_llm` uses `user` role for system-level prompt**~~ — CLOSED: the classification call is split into `system` (taxonomy instructions from src/prompts.py `SYSTEM_PROMPT`) + `user` (log excerpt) via `build_classification_messages`, and src/classifier.py sends both messages (src/classifier.py). Regression fence: `test_build_messages_*` in tests/test_prompts.py + updated `test_pipeline_error_line_fed_to_classifier` in tests/test_integration.py.
