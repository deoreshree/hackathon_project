"""Lightweight chatbot service with in-memory conversation sessions."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from typing import Callable

from backend.response_builder import build_fact_check_response, split_evidence_by_stance
from backend.schemas import ChatResponse, FactCheckResponse
from rag.rag_pipeline import RAGPipeline, RAGResponse

MAX_SESSIONS = 200
FOLLOW_UP_PATTERNS = (
    r"^why\b",
    r"^how\b",
    r"^explain\b",
    r"^what evidence\b",
    r"^show (me )?(the )?evidence\b",
    r"^tell me more\b",
    r"^elaborate\b",
    r"^more details\b",
    r"^what do you mean\b",
    r"^can you explain\b",
    r"^sources\b",
    r"^what sources\b",
    r"^why\?$",
    r"^why though\b",
)


@dataclass
class ChatSession:
    session_id: str
    last_claim: str | None = None
    last_fact_check: FactCheckResponse | None = None
    messages: list[tuple[str, str]] = field(default_factory=list)


class ChatService:
    """Handles chat messages using the existing RAG pipeline."""

    def __init__(
        self,
        pipeline: RAGPipeline,
        *,
        build_response: Callable[[RAGResponse], FactCheckResponse] | None = None,
    ) -> None:
        self._pipeline = pipeline
        self._build_response = build_response or build_fact_check_response
        self._sessions: dict[str, ChatSession] = {}

    def handle_message(self, message: str, session_id: str | None = None) -> ChatResponse:
        normalized_message = message.strip()
        if not normalized_message:
            raise ValueError("Message cannot be empty.")

        session = self._get_or_create_session(session_id)
        session.messages.append(("user", normalized_message))

        if self._is_follow_up(normalized_message) and session.last_fact_check is not None:
            response = self._build_follow_up_response(session, normalized_message)
        else:
            rag_result = self._pipeline.run(normalized_message)
            fact_check = self._build_response(rag_result)
            session.last_claim = fact_check.claim
            session.last_fact_check = fact_check
            response = self._to_chat_response(
                session_id=session.session_id,
                message=normalized_message,
                fact_check=fact_check,
                is_follow_up=False,
            )

        session.messages.append(("assistant", response.answer))
        return response

    def _get_or_create_session(self, session_id: str | None) -> ChatSession:
        if session_id and session_id in self._sessions:
            return self._sessions[session_id]

        if len(self._sessions) >= MAX_SESSIONS:
            oldest_key = next(iter(self._sessions))
            del self._sessions[oldest_key]

        new_id = session_id or str(uuid.uuid4())
        session = ChatSession(session_id=new_id)
        self._sessions[new_id] = session
        return session

    def _is_follow_up(self, message: str) -> bool:
        lowered = message.lower().strip()
        if len(lowered.split()) > 12:
            return False
        return any(re.search(pattern, lowered) for pattern in FOLLOW_UP_PATTERNS)

    def _build_follow_up_response(
        self,
        session: ChatSession,
        message: str,
    ) -> ChatResponse:
        assert session.last_fact_check is not None
        fact_check = session.last_fact_check
        supporting, contradicting, neutral = split_evidence_by_stance(fact_check.evidence)

        answer_parts = [
            f"Here is the evidence behind the verdict {fact_check.verdict} "
            f'for the claim: "{fact_check.claim}".',
            fact_check.explanation,
        ]

        if supporting:
            answer_parts.append(
                "Supporting evidence: "
                + " | ".join(item.text for item in supporting[:3])
            )
        if contradicting:
            answer_parts.append(
                "Contradicting evidence: "
                + " | ".join(item.text for item in contradicting[:3])
            )
        if not supporting and not contradicting:
            answer_parts.append(
                "There is insufficient reliable evidence to support a stronger conclusion."
            )

        answer = " ".join(part for part in answer_parts if part)

        return self._to_chat_response(
            session_id=session.session_id,
            message=message,
            fact_check=fact_check,
            is_follow_up=True,
            answer_override=answer,
        )

    def _to_chat_response(
        self,
        *,
        session_id: str,
        message: str,
        fact_check: FactCheckResponse,
        is_follow_up: bool,
        answer_override: str | None = None,
    ) -> ChatResponse:
        supporting, contradicting, neutral = split_evidence_by_stance(fact_check.evidence)
        answer = answer_override or self._build_final_answer(fact_check)

        return ChatResponse(
            session_id=session_id,
            message=message,
            verdict=fact_check.verdict,
            confidence=fact_check.confidence,
            answer=answer,
            explanation=fact_check.explanation,
            supporting_evidence=supporting,
            contradicting_evidence=contradicting,
            neutral_evidence=neutral,
            sources=fact_check.sources,
            is_follow_up=is_follow_up,
        )

    @staticmethod
    def _build_final_answer(fact_check: FactCheckResponse) -> str:
        verdict_text = {
            "SUPPORTED": "The claim appears supported by the retrieved evidence.",
            "CONTRADICTED": "The claim appears contradicted by the retrieved evidence.",
            "MIXED": "The retrieved evidence is mixed on this claim.",
            "UNVERIFIED": "There is insufficient reliable evidence to verify this claim.",
        }.get(fact_check.verdict, "The claim could not be verified confidently.")

        if fact_check.explanation and fact_check.explanation != "No explanation available.":
            return f"{verdict_text} {fact_check.explanation}"

        return verdict_text
