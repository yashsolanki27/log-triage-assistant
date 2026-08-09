# Tech Debt Tracker

Migrated from `reviewer-findings.md` on 2026-08-04 (findings 1-4, 6, 9,
11-15 — 11 items). Re-derived against current code on 2026-08-09 after the
v2.0 rewrite (several Part 4b fixes were lost in that rewrite and are marked
as reopened below).

---

## src/parser.py

1. **Silent fallback (patterns.md violation)** — `_extract_error_line` Priority 4 returns the first non-empty line with no indicator that it's a fallback, so callers cannot distinguish a confident extraction from a guess (src/parser.py). Debt not bug: output is still a usable line; the problem is the "no silent fallback" rule from docs/patterns.md is unenforced. Suggested fix: return an `is_fallback` flag alongside the line (the 3bf400b fix added it, but the v2.0 rewrite dropped it — reopened).

2. **No handling of binary/garbled input** — `parse_log` only rejects empty/whitespace text; embedded NUL bytes or non-UTF-8 sequences pass through with undefined behavior (src/parser.py). Debt not bug: an unvalidated encoding assumption, not a wrong result on valid input. Suggested fix: reject NUL bytes in `parse_log` and document the encoding assumption (was added at 3bf400b, dropped by the v2.0 rewrite — reopened).

3. ~~**Regex does not cover .NET-style `FaultException`**~~ — CLOSED: the Priority 1 regex `\b\w+(Exception|Error)\b` already matches `FaultException<Detail>`; `\w+` backtracks so `(Exception|Error)` matches `Exception`, and `\b` holds before `<`. Not debt. Regression test `test_parse_dotnet_fault_exception` was lost in the v2.0 rewrite — worth restoring as a fence.

---

## src/classifier.py

4. ~~**Docstring claims `OPENCODE_API_KEY` is used**~~ — CLOSED: `_get_api_keys` now states it reads the `OPENCODE_API_KEY` environment variable (comma-separated keys allowed, `OPENAI_API_KEY` fallback). Not debt.

5. **`_apply_confidence_rule` mutates in-place and returns** — The function modifies `result` directly and also returns it, making the data flow harder to reason about (src/classifier.py). Debt not bug: functionally correct, stylistically inconsistent. Suggested fix: return a new dict and stop mutating the input (the 3bf400b fix did exactly this, but the v2.0 rewrite regressed it — reopened).

6. ~~**`base_url` points to `opencode.ai/zen/v1`**~~ — CLOSED: now configurable via `OPENCODE_BASE_URL` env var and documented in docs/tech-stack.md. Not debt.

7. **No request timeout or rate limiting** — `/triage` calls the external LLM with no explicit timeout, so a slow or hung LLM call blocks the FastAPI worker indefinitely; no rate limiting means a burst of requests can exhaust the LLM quota (src/classifier.py, src/api.py). Debt not bug: robustness/ops hardening, not a correctness defect. Suggested fix: pass `timeout=` to `chat.completions.create` and add per-client rate limiting.

8. **`TriageResult.unclassified_reason` typed `str | None` with no conditional constraint** — The Pydantic model allows `None` even when category is `unclassified`, even though docs/business-logic.md requires a non-empty reason for unclassified results (src/api.py). Debt not bug: currently mitigated at the classifier layer (Finding 19), but the API contract itself is not self-enforcing. Suggested fix: re-add a `model_validator` requiring a non-empty reason when category=unclassified (was added at 3bf400b, dropped by the v2.0 rewrite — reopened).

---

## Cross-cutting / Documentation

9. **`docs/business-logic.md` category descriptions are terse** — Each category has a one-line description with no examples of what it looks like in practice, which makes classification quality hard to verify (docs/business-logic.md, mirrored in src/prompts.py). Debt not bug: documentation gap, not a code defect. Suggested fix: expand each category with signal keywords, distinguishing features, and example log lines (was done at 3bf400b, reverted by the v2.0 rewrite — reopened).

10. ~~**No integration test with real LLM**~~ — CLOSED: `tests/test_live_llm.py` (10 tests, `-m live`) now exercises the real OpenAI-compatible endpoint; excluded from default CI by design. Not debt.

11. **`_call_llm` uses `user` role for system-level prompt** — The classification prompt is a detailed system instruction but is sent as a `user` message; best practice is `system` role for the prompt and `user` role for the log excerpt only (src/classifier.py). Debt not bug: the model still responds correctly. Suggested fix: split messages into `system` (instructions) + `user` (log excerpt).
