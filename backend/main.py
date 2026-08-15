"""FastAPI backend for the AI Fake News Detector.

Security posture (Step 9):
- User input is validated by Pydantic schemas (length caps, blank rejection).
- Internal exceptions are never exposed to clients — safe messages only.
- Rate limiting protects public endpoints from accidental abuse.
- CORS origins are configurable via the CORS_ORIGINS environment variable.
- Secrets (API keys) live only in .env and are never returned to clients.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.chat_service import ChatService
from backend.rate_limit import RateLimiter, create_rate_limiter
from backend.response_builder import build_fact_check_response
from backend.schemas import ChatRequest, ChatResponse, FactCheckRequest, FactCheckResponse
from rag.rag_pipeline import RAGPipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(
    title="AI Fake News Detector API",
    description="RAG-based fact-checking API with chatbot",
    version="1.0.0",
)

# CORS: allow origins from CORS_ORIGINS (comma-separated) or default to "*".
# allow_credentials stays False so "*" remains a valid, safe configuration.
_cors_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "*").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins or ["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

pipeline = RAGPipeline()
chat_service = ChatService(pipeline, build_response=build_fact_check_response)

# Lightweight in-memory rate limiter for public endpoints.
app.state.rate_limiter: RateLimiter = create_rate_limiter()


# ---------------------------------------------------------------------------
# Security: safe exception handling
# ---------------------------------------------------------------------------


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Return a sanitized 422 — field/message only, never the raw input value."""
    errors: list[dict[str, str]] = []
    for err in exc.errors():
        location = ".".join(str(part) for part in err.get("loc", []) if part != "body")
        errors.append(
            {
                "field": location or "body",
                "message": str(err.get("msg", "Invalid value")),
            }
        )
    return JSONResponse(status_code=422, content={"detail": errors})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all: never leak internal exception details to clients."""
    logger.exception(
        "Unhandled exception on %s %s",
        request.method,
        request.url.path,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please try again later."},
    )


# ---------------------------------------------------------------------------
# Rate limiting dependency
# ---------------------------------------------------------------------------


def rate_limit_dependency(request: Request) -> None:
    """Reject requests once the per-client limit is exceeded (HTTP 429)."""
    limiter: RateLimiter = request.app.state.rate_limiter
    client_ip = request.client.host if request.client else "unknown"
    if not limiter.allow(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please slow down and try again shortly.",
        )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/")
def root():
    return {
        "message": "AI Fake News Detector API",
        "status": "running",
        "version": "1.0.0",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "fact-checking-api",
    }


@app.get("/chat", response_class=HTMLResponse)
def chat_page():
    """Serve the chatbot HTML interface."""
    index_path = STATIC_DIR / "index.html"
    try:
        return HTMLResponse(content=index_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return HTMLResponse(
            content="<h1>Error: static/index.html not found</h1>",
            status_code=404,
        )


@app.post("/api/fact-check", response_model=FactCheckResponse)
def fact_check(request: FactCheckRequest, _: None = Depends(rate_limit_dependency)):
    try:
        rag_result = pipeline.run(request.claim)
        return build_fact_check_response(rag_result)
    except ValueError as exc:
        # Safe, user-facing message — input problems only, no internals.
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Fact-checking pipeline failed")
        raise HTTPException(
            status_code=500,
            detail="Fact-checking failed due to an internal error. Please try again.",
        ) from exc


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, _: None = Depends(rate_limit_dependency)):
    """Fact-checking chatbot endpoint with lightweight conversation support."""
    try:
        return chat_service.handle_message(request.message, request.session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Chatbot request failed")
        raise HTTPException(
            status_code=500,
            detail="Chatbot failed due to an internal error. Please try again.",
        ) from exc
