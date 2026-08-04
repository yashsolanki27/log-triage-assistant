# Patterns

- One function, one responsibility (parser ≠ classifier ≠ API)
- No silent fallback: unclassified is a valid output, not an error to hide
- All LLM prompts stored in src/prompts.py, not inline in classifier.py
