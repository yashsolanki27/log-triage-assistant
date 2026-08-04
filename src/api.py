"""FastAPI layer — exposes POST /triage endpoint.

Body: {log_text: str}
Calls parser → classifier, returns JSON result.

Patterns: one function, one responsibility. No silent fallback.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from src.classifier import classify_log
from src.parser import parse_log

app = FastAPI(title="Log Triage Assistant", version="0.1.0")


class TriageRequest(BaseModel):
    """Request body for /triage endpoint."""

    log_text: str = Field(..., min_length=1, description="Raw log text to classify")


class TriageResponse(BaseModel):
    """Response body for /triage endpoint."""

    category: str
    root_cause_summary: str
    confidence: int
    suggested_action: str
    unclassified_reason: str | None


@app.post("/triage", response_model=TriageResponse)
def triage(request: TriageRequest) -> dict:
    """Classify a log entry and return root cause analysis.

    Steps:
    1. Parse raw log text → extract error line.
    2. Classify via LLM → category, confidence, summary.
    3. Return structured result.
    """
    try:
        parsed = parse_log(request.log_text)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        result = classify_log(parsed)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=f"Classification failed: {exc}") from exc

    return result
