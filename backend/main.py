from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from rag.rag_pipeline import RAGPipeline
from rag.verifier import VerificationStatus
from rag.models import EvidenceItem
from rag.sources import SourceCitation

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="AI Fake News Detector API",
    description="RAG-based fact-checking API with chatbot",
    version="1.0.0",
)

# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# STATIC FILES (for chatbot UI)
# ============================================================

app.mount("/static", StaticFiles(directory="static"), name="static")

# ============================================================
# RAG PIPELINE (singleton)
# ============================================================

pipeline = RAGPipeline()

# ============================================================
# REQUEST MODEL
# ============================================================

class FactCheckRequest(BaseModel):
    claim: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="News claim or statement to fact-check",
    )

# ============================================================
# RESPONSE MODELS
# ============================================================

class EvidenceResponse(BaseModel):
    """Evidence item with its stance classification."""
    text: str
    source: str
    url: str
    title: str
    relevance_score: float | None
    stance: str  # "supporting", "contradicting", or "neutral"

class SourceResponse(BaseModel):
    """Source citation."""
    url: str
    title: str | None = None
    publisher: str | None = None

class FactCheckResponse(BaseModel):
    claim: str
    verdict: str          # "SUPPORTED", "CONTRADICTED", "MIXED", "UNVERIFIED"
    confidence: float     # 0.0 to 1.0
    evidence: list[EvidenceResponse]
    explanation: str
    sources: list[SourceResponse]

# ============================================================
# HEALTH CHECKS
# ============================================================

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

# ============================================================
# CHATBOT UI
# ============================================================

@app.get("/chat", response_class=HTMLResponse)
def chat_page():
    """Serve the chatbot HTML interface."""
    try:
        with open("static/index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(
            content="<h1>Error: static/index.html not found</h1>",
            status_code=404,
        )

# ============================================================
# FACT CHECK ENDPOINT
# ============================================================

@app.post("/api/fact-check", response_model=FactCheckResponse)
def fact_check(request: FactCheckRequest):
    try:
        rag_result = pipeline.run(request.claim)
        response = _build_response(rag_result)
        return response
    except ValueError as exc:
        # Raised by pipeline for empty claim or invalid input
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Fact-checking pipeline failed")
        raise HTTPException(
            status_code=500,
            detail=f"Fact-checking failed: {exc}",
        ) from exc

# ============================================================
# RESPONSE BUILDER
# ============================================================

def _build_response(rag_result: Any) -> FactCheckResponse:
    """Convert RAGPipeline output to the API response model."""
    verification = rag_result.verification
    status = verification.status

    # Map status to simplified verdict strings
    verdict_map = {
        VerificationStatus.LIKELY_TRUE: "SUPPORTED",
        VerificationStatus.LIKELY_FALSE: "CONTRADICTED",
        VerificationStatus.MIXED: "MIXED",
        VerificationStatus.UNVERIFIED: "UNVERIFIED",
    }
    verdict = verdict_map.get(status, "UNVERIFIED")

    # Compute confidence (weighted support fraction)
    sup_weight = sum(_compute_weight(item) for item in verification.supporting)
    con_weight = sum(_compute_weight(item) for item in verification.contradicting)
    total_weight = sup_weight + con_weight
    if total_weight > 0:
        confidence = sup_weight / total_weight
    else:
        confidence = 0.5
    confidence = round(max(0.0, min(1.0, confidence)), 3)

    # Build evidence list with stance
    evidence_list = []
    for item in verification.supporting:
        evidence_list.append(EvidenceResponse(
            text=item.text,
            source=item.source,
            url=item.url,
            title=item.title,
            relevance_score=item.relevance_score,
            stance="supporting",
        ))
    for item in verification.contradicting:
        evidence_list.append(EvidenceResponse(
            text=item.text,
            source=item.source,
            url=item.url,
            title=item.title,
            relevance_score=item.relevance_score,
            stance="contradicting",
        ))
    for item in verification.neutral:
        evidence_list.append(EvidenceResponse(
            text=item.text,
            source=item.source,
            url=item.url,
            title=item.title,
            relevance_score=item.relevance_score,
            stance="neutral",
        ))

    # Extract explanation text
    explanation_text = "No explanation available."
    if rag_result.explanation:
        explanation_text = rag_result.explanation.text

    # Build sources from citations
    sources = []
    for citation in rag_result.citations:
        sources.append(SourceResponse(
            url=citation.url,
            title=citation.title,
            publisher=citation.publisher or getattr(citation, "source", None),
        ))

    return FactCheckResponse(
        claim=rag_result.claim,
        verdict=verdict,
        confidence=confidence,
        evidence=evidence_list,
        explanation=explanation_text,
        sources=sources,
    )

def _compute_weight(item: EvidenceItem) -> float:
    """Compute weight for confidence (relevance + authority bonus)."""
    relevance = item.relevance_score if item.relevance_score is not None else 0.5
    # Simplified authority bonus – we could import match_source, but keep it simple.
    return relevance