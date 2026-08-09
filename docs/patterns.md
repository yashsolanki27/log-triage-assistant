# Patterns

- One function, one responsibility (parser ≠ classifier ≠ API)
- No silent fallback: unclassified is a valid output, not an error to hide
- All LLM prompts stored in src/prompts.py, not inline in classifier.py
- A function that returns a dict must not mutate the dict it was given —
  build and return a new dict so callers' data flow stays unambiguous
