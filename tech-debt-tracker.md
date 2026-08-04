# Tech Debt Tracker

Migrated from `reviewer-findings.md` on 2026-08-04.

---

## src/parser.py

1. **Silent fallback (patterns.md violation)** — `_extract_error_line` Priority 4 returns the first non-empty line with no indicator that it's a fallback. The "no silent fallback" rule applies here: callers cannot distinguish a confident extraction from a guess. Consider adding a flag or logging when falling back to the generic first line.

2. ~~**No handling of binary/garbled input**~~ — Fixed: Added NUL byte validation in `parse_log` and documented encoding assumption in docstring. Tests added in `test_parser.py`.

3. ~~**Regex does not cover .NET-style `FaultException`**~~ — Closed: regex already matches. `\w+` backtracks so `(Exception|Error)` matches `Exception`, and `\b` matches before `<` (word→non-word boundary). Test added: `test_parse_dotnet_fault_exception`.

---

## src/classifier.py

4. ~~**Docstring claims `OPENCODE_API_KEY` is used; code reads `OPENCODE_API_KEY`** — The docstring at line 33 says "If None, uses OPENCODE_API_KEY" which is ambiguous (could mean "uses the key named OPENCODE_API_KEY" or "uses the client named OPENCODE_API_KEY"). Should state: "reads the `OPENCODE_API_KEY` environment variable."~~ **FIXED**

5. ~~**`_apply_confidence_rule` mutates in-place and returns** — The function modifies `result` directly and also returns it. While not a bug, it's inconsistent with a functional style and makes the data flow harder to reason about. Minor style issue.~~ **FIXED**

6. ~~**`base_url` points to `opencode.ai/zen/v1`** — This is a non-standard endpoint. No documentation or env-var override exists. If the endpoint changes, classifier breaks.~~ **FIXED**

---

## src/api.py

7. **No request timeout or rate limiting** — The `/triage` endpoint calls an external LLM with no timeout. A slow or hung LLM call will block the FastAPI worker indefinitely. No rate limiting exists either, so a burst of requests could exhaust LLM quotas.

8. **`TriageResponse.unclassified_reason` typed as `str | None`** — When category is not `unclassified`, the field is `None`. When it is `unclassified`, it should always be a non-empty string per business-logic.md. The Pydantic model doesn't enforce this conditional constraint.

---

## Cross-cutting / Documentation

9. **`docs/business-logic.md` category descriptions are terse** — Each category has a one-line description. The classifier's prompt in `src/prompts.py` mirrors these exactly, but there are no examples of what each category looks like in practice. This makes it hard to verify classification quality.

10. **No integration test with real LLM** — All classifier tests mock the LLM. No test exercises the actual OpenAI endpoint, so prompt regressions or API changes won't be caught until production.

11. **`_call_llm` uses `user` role for system-level prompt** — The prompt is a detailed system instruction but is sent as a `user` message. Best practice is to use `system` role for the prompt and `user` role for the log excerpt only.

---

## Future ideas

- **Batch/multi-entry log support** — Deferred. Rationale: v1 architecture is single-entry by design, no real usage data yet to size the feature correctly. Revisit if real usage shows need for correlation across entries.
