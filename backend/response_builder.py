"""Map RAG pipeline output to API response models."""

from __future__ import annotations

from typing import Any

from rag.models import EvidenceItem
from rag.verifier import VerificationStatus

from backend.schemas import EvidenceResponse, FactCheckResponse, SourceResponse


def build_fact_check_response(rag_result: Any) -> FactCheckResponse:
    """Convert RAGPipeline output to the API response model."""
    verification = rag_result.verification
    status = verification.status

    verdict_map = {
        VerificationStatus.LIKELY_TRUE: "SUPPORTED",
        VerificationStatus.LIKELY_FALSE: "CONTRADICTED",
        VerificationStatus.MIXED: "MIXED",
        VerificationStatus.UNVERIFIED: "UNVERIFIED",
    }
    verdict = verdict_map.get(status, "UNVERIFIED")

    sup_weight = sum(_compute_weight(item) for item in verification.supporting)
    con_weight = sum(_compute_weight(item) for item in verification.contradicting)
    total_weight = sup_weight + con_weight
    confidence = sup_weight / total_weight if total_weight > 0 else 0.5
    confidence = round(max(0.0, min(1.0, confidence)), 3)

    evidence_list: list[EvidenceResponse] = []
    for item in verification.supporting:
        evidence_list.append(_evidence_to_response(item, "supporting"))
    for item in verification.contradicting:
        evidence_list.append(_evidence_to_response(item, "contradicting"))
    for item in verification.neutral:
        evidence_list.append(_evidence_to_response(item, "neutral"))

    explanation_text = "No explanation available."
    if rag_result.explanation:
        explanation_text = rag_result.explanation.text

    sources = [
        SourceResponse(
            url=citation.url,
            title=citation.title,
            publisher=citation.publisher or getattr(citation, "source", None),
        )
        for citation in rag_result.citations
    ]

    return FactCheckResponse(
        claim=rag_result.claim,
        verdict=verdict,
        confidence=confidence,
        evidence=evidence_list,
        explanation=explanation_text,
        sources=sources,
    )


def split_evidence_by_stance(
    evidence: list[EvidenceResponse],
) -> tuple[list[EvidenceResponse], list[EvidenceResponse], list[EvidenceResponse]]:
    """Split combined evidence list into stance buckets."""
    supporting = [item for item in evidence if item.stance == "supporting"]
    contradicting = [item for item in evidence if item.stance == "contradicting"]
    neutral = [item for item in evidence if item.stance == "neutral"]
    return supporting, contradicting, neutral


def _evidence_to_response(item: EvidenceItem, stance: str) -> EvidenceResponse:
    return EvidenceResponse(
        text=item.text,
        source=item.source,
        url=item.url,
        title=item.title,
        relevance_score=item.relevance_score,
        stance=stance,
    )


def _compute_weight(item: EvidenceItem) -> float:
    return item.relevance_score if item.relevance_score is not None else 0.5
