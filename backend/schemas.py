"""API request/response schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class FactCheckRequest(BaseModel):
    claim: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="News claim or statement to fact-check",
    )


class EvidenceResponse(BaseModel):
    text: str
    source: str
    url: str
    title: str
    relevance_score: float | None
    stance: str


class SourceResponse(BaseModel):
    url: str
    title: str | None = None
    publisher: str | None = None


class FactCheckResponse(BaseModel):
    claim: str
    verdict: str
    confidence: float
    evidence: list[EvidenceResponse]
    explanation: str
    sources: list[SourceResponse]


class ChatRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="User message or claim to fact-check",
    )
    session_id: str | None = Field(
        default=None,
        max_length=128,
        description="Optional conversation session id for follow-up questions",
    )


class ChatResponse(BaseModel):
    session_id: str
    message: str
    verdict: str
    confidence: float
    answer: str
    explanation: str
    supporting_evidence: list[EvidenceResponse]
    contradicting_evidence: list[EvidenceResponse]
    neutral_evidence: list[EvidenceResponse] = Field(default_factory=list)
    sources: list[SourceResponse]
    is_follow_up: bool = False
