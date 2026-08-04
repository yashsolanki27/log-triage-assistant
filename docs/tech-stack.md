# Tech Stack

- Backend: Python 3.11+, FastAPI
- LLM: OpenCode Zen (DeepSeek V4 Flash Free), single classification call per log entry
- Frontend: Streamlit (fast, matches solo-dev scope)
- Storage: none needed v1 — stateless classify-in, result-out
- Testing: pytest

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENCODE_API_KEY` | (required) | API key for LLM endpoint |
| `OPENCODE_BASE_URL` | `https://opencode.ai/zen/v1` | LLM API base URL |
| `LLM_MODEL_NAME` | `deepseek-v4-flash-free` | Model identifier |
