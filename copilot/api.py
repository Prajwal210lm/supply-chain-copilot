"""FastAPI surface over the pipeline. Four endpoints: health (db row count,
keyless), catalog (metric/dimension metadata, keyless), demo (a cached
pre-built conversation, keyless, no LLM), and ask (the live pipeline —
gated by a required secret, server-side throttles, and a fail-closed
startup check). The Anthropic client is injected via a factory dependency
so the keyless paths never construct one and /api/ask is testable with a
mock at zero credit.

Security/throttling model mirrors the prior project's (P3, the OTIF
root-cause engine) FastAPI layer: exact-origin CORS, an in-memory per-IP +
daily counter under one lock, a process-wide Semaphore(1) so a request
burst can't fan out into parallel paid calls, and a fail-closed startup
check rather than fail-open. The specific numbers here (10 questions/hour,
DAILY_RUN_CAP default 50) are this project's own, not copied from P3.
"""

import json
import logging
import os
import threading
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from dataclasses import fields, is_dataclass
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from copilot import constants as C
from copilot import db, pipeline, registry, stage1

logger = logging.getLogger("copilot.api")

RATE_LIMIT_PER_IP_PER_HOUR = 10
RATE_LIMIT_WINDOW_SECONDS = 3600

DEMO_CONVERSATION_PATH = C.PROJECT_ROOT / "data" / "demo_conversation.json"


def _daily_cap() -> int:
    return int(os.environ.get("DAILY_RUN_CAP", "50"))


def get_llm_factory():
    """Zero-arg factory that builds the real client. Resolved on every
    request but only CALLED on /api/ask's path, so /api/health, /api/demo,
    and /api/catalog never construct one. Tests override this dependency."""
    def make():
        from copilot.client import AnthropicClient
        return AnthropicClient()
    return make


# --------------------------------------------------------------------------
# Fail-closed configuration guards
# --------------------------------------------------------------------------

def _ask_disabled_reason() -> str | None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return "ANTHROPIC_API_KEY is not set."
    if not os.environ.get("API_SECRET"):
        return "API_SECRET is not set."
    return None


@asynccontextmanager
async def _lifespan(app: FastAPI):
    reason = _ask_disabled_reason()
    if reason:
        logger.warning("POST /api/ask is disabled at startup: %s", reason)
    if not os.environ.get("FRONTEND_ORIGIN"):
        logger.warning(
            "FRONTEND_ORIGIN is not set; only localhost origins are allowed by CORS. "
            "Set FRONTEND_ORIGIN to your deployed frontend URL in production."
        )
    yield


app = FastAPI(title="Supply Chain Copilot", lifespan=_lifespan)

# Exact origins only: localhost for dev, plus whatever FRONTEND_ORIGIN names.
# No wildcard — an unset FRONTEND_ORIGIN means no non-local browser origin
# can call this API (the startup warning above says so).
_origins = [o.strip() for o in os.environ.get("FRONTEND_ORIGIN", "").split(",") if o.strip()] + [
    "http://localhost:3000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# --------------------------------------------------------------------------
# Server-side throttling — in-memory, correct for a single-instance
# deployment (this project's scale), not for multiple replicas. Concurrency
# is capped process-wide at one live pipeline run so a burst of requests
# cannot fan out into parallel paid LLM calls.
# --------------------------------------------------------------------------

_state_lock = threading.Lock()
_ip_hits: dict = defaultdict(list)
_daily = {"date": None, "count": 0}
_run_semaphore = threading.Semaphore(1)


def _reserve_run_slot(ip: str) -> str | None:
    """Atomically checks the daily cap and the per-IP rate limit and, if
    both pass, books the attempt. Returns an error message if the request
    should be rejected, else None. Checking and booking happen under one
    lock so concurrent requests cannot race past either limit."""
    now = time.time()
    today = datetime.now(timezone.utc).date().isoformat()
    with _state_lock:
        if _daily["date"] != today:
            _daily["date"] = today
            _daily["count"] = 0
        cap = _daily_cap()
        if _daily["count"] >= cap:
            return f"Daily limit of {cap} questions reached. Try again tomorrow."
        hits = [t for t in _ip_hits[ip] if now - t < RATE_LIMIT_WINDOW_SECONDS]
        if len(hits) >= RATE_LIMIT_PER_IP_PER_HOUR:
            return f"Rate limit: max {RATE_LIMIT_PER_IP_PER_HOUR} questions per hour per IP."
        hits.append(now)
        _ip_hits[ip] = hits
        _daily["count"] += 1
        return None


def _release_run_slot(ip: str) -> None:
    """Undo a reservation booked by _reserve_run_slot when the run fails
    upstream (model billing/timeout/error), so an outage doesn't burn the
    daily cap or the caller's hourly allowance. Safe because Semaphore(1)
    serializes the reserve/run/release window, so the last recorded hit for
    this IP is the one we just booked."""
    with _state_lock:
        if _daily["count"] > 0:
            _daily["count"] -= 1
        hits = _ip_hits.get(ip)
        if hits:
            hits.pop()


# --------------------------------------------------------------------------
# Serialization helpers
# --------------------------------------------------------------------------

def _to_plain(obj):
    if is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: _to_plain(getattr(obj, f.name)) for f in fields(obj)}
    if isinstance(obj, tuple):
        return [_to_plain(item) for item in obj]
    return obj


def _chart_response(chart_spec) -> dict | None:
    if chart_spec is None:
        return None
    plain = _to_plain(chart_spec)
    points = plain.pop("points")
    return {
        "type": plain["type"],
        "title": plain["title"],
        "data": points,
        "axes": {"x": plain["x_label"], "y": plain["y_label"]},
    }


def _ask_response(result: pipeline.PipelineResult) -> dict:
    usage = {
        "input_tokens": result.usage.input_tokens,
        "output_tokens": result.usage.output_tokens,
        "cost_usd": result.usage.cost_usd,
    }

    if result.outcome_kind == "clarification":
        return {
            "type": "clarification", "spec": result.spec, "echo_bar": None, "result": None, "narration": None,
            "narration_withheld": None, "chart": None, "sql": None,
            "options": result.spec.get("options"), "suggestions": None, "message": None, "usage": usage,
        }
    if result.outcome_kind == "refusal":
        return {
            "type": "refusal", "spec": result.spec, "echo_bar": None, "result": None, "narration": None,
            "narration_withheld": None, "chart": None, "sql": None,
            "options": None, "suggestions": result.spec.get("suggestions"), "message": result.spec.get("message"), "usage": usage,
        }
    return {
        "type": "answer", "spec": result.spec, "echo_bar": result.echo_bar, "result": _to_plain(result.result),
        "narration": result.narration, "narration_withheld": result.withheld_reason,
        "chart": _chart_response(result.chart_spec), "sql": result.query_sql,
        "options": None, "suggestions": None, "message": None, "usage": usage,
    }


# --------------------------------------------------------------------------
# Endpoints
# --------------------------------------------------------------------------

@app.get("/api/health")
def health():
    con = db.connect(C.DB_PATH)
    try:
        db_rows = con.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    finally:
        con.close()
    return {"status": "ok", "db_rows": db_rows}


@app.get("/api/catalog")
def catalog():
    metrics = [
        {
            "key": key,
            "display_name": entry.display_name,
            "definition": entry.definition,
            "synonyms": list(entry.synonyms),
            "disambiguation_note": entry.disambiguation_note,
            "decomposable": entry.decomposable,
            "compatible_dimensions": sorted(entry.compatible_dimensions),
        }
        for key, entry in registry.METRICS.items()
    ]
    dimensions = []
    for dim in ("month", "week", "dc", "emirate", "category", "customer_segment", "supplier"):
        members = registry.DIMENSION_MEMBERS.get(dim)
        dimensions.append({
            "key": dim,
            "members": [{"code": code, "display": display} for code, display in members] if members else None,
        })
    return {"metrics": metrics, "dimensions": dimensions}


@app.get("/api/demo")
def demo():
    if not DEMO_CONVERSATION_PATH.exists():
        raise HTTPException(status_code=404, detail="demo conversation not found")
    with open(DEMO_CONVERSATION_PATH, encoding="utf-8") as f:
        return json.load(f)


@app.post("/api/ask")
def ask(
    payload: dict,
    request: Request,
    make_llm=Depends(get_llm_factory),
    x_api_secret: str = Header(None),
):
    disabled = _ask_disabled_reason()
    if disabled:
        logger.warning("POST /api/ask refused: %s", disabled)
        raise HTTPException(status_code=503, detail="Service unavailable")

    secret = os.environ.get("API_SECRET")
    if x_api_secret != secret:
        raise HTTPException(status_code=403, detail="Missing or invalid X-Api-Secret header")

    question = payload.get("question")
    if not question or not isinstance(question, str):
        raise HTTPException(status_code=422, detail="'question' is required")
    context = payload.get("context") or []

    ip = request.client.host if request.client else "unknown"

    if not _run_semaphore.acquire(blocking=False):
        return JSONResponse(
            status_code=429,
            content={"detail": "Another question is already being answered. Try again shortly."},
        )
    try:
        limit_msg = _reserve_run_slot(ip)
        if limit_msg:
            return JSONResponse(status_code=429, content={"detail": limit_msg})

        ts = datetime.now(timezone.utc).isoformat()
        logger.info("ask start ts=%s ip=%s", ts, ip)

        try:
            context_turns = [stage1.ContextTurn(question=t["question"], spec=t["spec"]) for t in context]
            client_instance = make_llm()
            result = pipeline.run_question(question, context_turns=context_turns, client_instance=client_instance)
        except Exception:
            # Upstream failure (model billing/timeout/error). Refund the booked
            # slot and return a typed JSON error by RETURNING (not raising): a
            # returned response flows back out through CORSMiddleware and carries
            # the Access-Control-Allow-Origin header, whereas an unhandled
            # exception is caught outside CORS and reaches the browser header-less
            # (surfacing as an opaque "couldn't reach the API").
            _release_run_slot(ip)
            logger.exception("ask upstream error ts=%s ip=%s", ts, ip)
            return JSONResponse(
                status_code=502,
                content={
                    "type": "error",
                    "message": "The AI service is temporarily unavailable. Your question wasn't counted.",
                },
            )

        logger.info(
            "ask done ts=%s ip=%s outcome=%s tokens_in=%s tokens_out=%s",
            ts, ip, result.outcome_kind, result.usage.input_tokens, result.usage.output_tokens,
        )
        return _ask_response(result)
    finally:
        _run_semaphore.release()
