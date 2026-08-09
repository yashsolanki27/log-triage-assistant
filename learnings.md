# Learnings

Session learnings that are not yet durable enough for docs/. At the end of each
reviewer pass, this file is reviewed and durable lessons are promoted into
docs/ (see AGENTS.md memory rules).

---

## 2026-08-09 — first entry (post v1.1 / v2.0 review)

### SQLite was added late, and the docs lagged behind it
The v1 spec said "no storage needed v1 — stateless classify-in, result-out"
(docs/tech-stack.md). The History and Dashboard screens then forced a v1.1
extension (`src/db.py`), so the "no storage" note had to be superseded and the
storage layer kept isolated behind a tiny interface so the stateless core
(parser, prompts, classifier) stayed untouched (see `src/db.py` module docstring).
Lesson: when a later unit expands the data flow, update tech-stack.md +
architecture.md in the same change — the docs drift is what bites, not the code.

### Vanilla JS over Streamlit was the right call, and it was a call
The brief asked for a premium dark theme with fine-grained responsive control,
animated gauges, and SVG charts. That is straightforward in hand-written
CSS/JS and awkward inside Streamlit's component model (README "Architecture
Decisions"). The Streamlit app was kept as a deprecated alternative instead of
deleted. Lesson: pick the frontend framework for the design brief, not for
convenience; keep a deprecated path only while it still has value.

### The LLM wraps JSON in fences — parse defensively
Finding 8 in reviewer-findings.md: `_parse_response` called `json.loads`
directly and any ```json``` fenced reply raised a RuntimeError. The fix strips
markdown fences before parsing. Lesson: LLM output is untrusted text, not data;
normalize it before `json.loads`. This is the difference between a brittle
classifier and one that survives real models.

### `unclassified_reason` is a contract, not a nicety
Two separate findings (5 and 19 in reviewer-findings.md) hit the same gap from
different angles: `_validate_output` didn't enforce a non-empty reason, and
`_apply_confidence_rule` only guaranteed one when confidence was below the 70%
threshold — so a high-confidence `category=unclassified` reply could store a
null reason, contradicting patterns.md ("unclassified is a valid output, never
a silently hidden one"). Both were fixed in code, and each fix got a regression
test. Lesson: an invariant tied to a category ("unclassified always carries a
reason") needs enforcement in code, not just in the prompt — and it needs to be
checked at every layer that touches the field.

### v2.0 rewrites can silently eat earlier fixes
The v2.0 rewrite (1286e68) dropped several Part 4b fixes: the parser
`is_fallback` flag, NUL-byte validation, the api.py `model_validator` on
`unclassified_reason`, and the expanded business-logic.md category notes — yet
`reviewer-findings.md` still claimed findings 1-4, 6, 9, 11-15 had been "moved
to tech-debt-tracker.md", which was actually empty. Lesson: a "docs sync"
commit that empties a tracker while another file still references it is a
broken handoff; re-scan the tracker against the code after any large rewrite,
and re-verify moved findings are actually present.

### Multi-key failover for the LLM endpoint
`OPENCODE_API_KEY` accepts a comma-separated list; the classifier rotates to
the next key on auth/rate-limit errors instead of failing on the first one
(cover: test_classify_rotates_to_next_key_on_auth_error). Lesson: an
auto-switch makes the free-tier key rotation survivable without code changes —
worth keeping in mind for any LLM-backed integration.
