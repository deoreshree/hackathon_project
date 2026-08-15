from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from backend.chat_service import ChatService
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

pipeline = RAGPipeline()
chat_service = ChatService(pipeline, build_response=build_fact_check_response)


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
def fact_check(request: FactCheckRequest):
    try:
        rag_result = pipeline.run(request.claim)
        return build_fact_check_response(rag_result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Fact-checking pipeline failed")
        raise HTTPException(
            status_code=500,
            detail=f"Fact-checking failed: {exc}",
        ) from exc


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """Fact-checking chatbot endpoint with lightweight conversation support."""
    try:
        return chat_service.handle_message(request.message, request.session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Chatbot request failed")
        raise HTTPException(
            status_code=500,
            detail=f"Chatbot failed: {exc}",
        ) from exc
