"""FastAPI layer — Unit 4.

POST /triage        body: {log_text: str}      -> parser -> classifier -> stored result
GET  /history        query: limit, offset, category -> past triage results
GET  /triage/{id}     -> single stored triage result
GET  /stats          -> aggregate counts for the dashboard

Also serves the static frontend from /web at "/", so the whole app runs
from a single `uvicorn src.api:app` process.
"""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src import db
from src.classifier import classify_log
from src.parser import parse_log

# Initialise the DB at import time (not just on ASGI startup) so the app
# works correctly under test clients that don't trigger lifespan events.
db.init_db()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="Log Triage Assistant API", version="1.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class TriageRequest(BaseModel):
    log_text: str = Field(..., min_length=1, description="Raw pasted log text")


class TriageResult(BaseModel):
    id: int
    created_at: str
    raw_text: str
    extracted_error_line: str
    category: str
    root_cause_summary: str
    confidence: int
    suggested_action: str
    unclassified_reason: Optional[str] = None


@app.post("/triage", response_model=TriageResult)
def triage(request: TriageRequest):
    if not request.log_text.strip():
        raise HTTPException(status_code=422, detail="log_text must be non-empty")

    try:
        parsed = parse_log(request.log_text)
        result = classify_log(parsed)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    saved = db.save_triage(parsed, result)
    return saved


@app.get("/history", response_model=list[TriageResult])
def history(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    category: Optional[str] = Query(None),
):
    return db.list_triages(limit=limit, offset=offset, category=category)


@app.get("/triage/{triage_id}", response_model=TriageResult)
def get_triage(triage_id: int):
    result = db.get_triage(triage_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Triage not found")
    return result


@app.get("/stats")
def stats():
    return db.get_stats()


@app.get("/health")
def health():
    return {"status": "ok"}


# --- Static frontend ---------------------------------------------------
_WEB_DIR = Path(__file__).resolve().parent.parent / "web"

if _WEB_DIR.exists():
    app.mount("/assets", StaticFiles(directory=_WEB_DIR), name="assets")

    @app.get("/")
    def index():
        return FileResponse(_WEB_DIR / "index.html")
