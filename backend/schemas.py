"""API request/response schemas.

All user-supplied strings are validated here:
- claims/messages are stripped and must not be blank or whitespace-only
- length caps prevent oversized payloads from reaching the RAG pipeline
- optional fields (e.g. session_id) are stripped and length-limited
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

# Reasonable caps for a hackathon demo. Long enough for real fact-checking
# claims and chat messages, short enough to stop abuse.
MAX_CLAIM_LENGTH = 5000
MAX_MESSAGE_LENGTH = 5000
MAX_SESSION_ID_LENGTH = 128


class FactCheckRequest(BaseModel):
    claim: str = Field(
        ...,
        min_length=1,
        max_length=MAX_CLAIM_LENGTH,
        description="News claim or statement to fact-check",
    )

    @field_validator("claim")
    @classmethod
    def claim_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Claim cannot be empty or whitespace-only.")
        return stripped


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
        max_length=MAX_MESSAGE_LENGTH,
        description="User message or claim to fact-check",
    )
    session_id: str | None = Field(
        default=None,
        max_length=MAX_SESSION_ID_LENGTH,
        description="Optional conversation session id for follow-up questions",
    )

    @field_validator("message")
    @classmethod
    def message_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Message cannot be empty or whitespace-only.")
        return stripped

    @field_validator("session_id")
    @classmethod
    def session_id_stripped(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


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
