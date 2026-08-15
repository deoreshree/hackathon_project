"""Tests for the complete RAG pipeline (Step 6) and its failure handling.

All tests are deterministic and offline: retrieval uses fixture providers and
explanations use the NoOp provider (rule-based fallback) — no real API calls.
"""

from __future__ import annotations

import pytest

from rag.exceptions import RetrievalError
from rag.explainer import Explainer, NoOpLLMProvider
from rag.models import RetrievedDocument
from rag.providers import EmptyRetrievalProvider, FixtureRetrievalProvider
from rag.rag_pipeline import MAX_CLAIM_LENGTH, RAGPipeline
from rag.retriever import Retriever
from rag.verifier import VerificationStatus


def _documents() -> list[RetrievedDocument]:
    return [
        RetrievedDocument(
            title="Official vaccine safety review",
            url="https://www.who.int/vaccine-safety-review",
            source="World Health Organization",
            content=(
                "Studies confirm that vaccines are safe and effective for the "
                "general population. Health authorities verified the data and "
                "the evidence supports widespread use."
            ),
            relevance_score=0.9,
        ),
        RetrievedDocument(
            title="Fact check: vaccine microchip claim",
            url="https://www.snopes.com/fact-check/vaccine-microchip",
            source="Snopes",
            content=(
                "The claim that vaccines contain microchips is false and has "
                "been debunked. Investigators found no evidence of tracking "
                "hardware in any approved vaccine."
            ),
            relevance_score=0.85,
        ),
    ]


@pytest.fixture
def full_pipeline() -> RAGPipeline:
    return RAGPipeline(
        retriever=Retriever(provider=FixtureRetrievalProvider(_documents())),
        explainer=Explainer(provider=NoOpLLMProvider()),
    )


def test_rag_pipeline_initializes():
    pipeline = RAGPipeline()

    assert pipeline.retriever is not None
    assert pipeline.evidence_extractor is not None
    assert pipeline.verifier is not None
    assert pipeline.explainer is not None


def test_full_pipeline_returns_evidence_and_verdict(full_pipeline: RAGPipeline) -> None:
    result = full_pipeline.run("COVID vaccines contain microchips.")

    assert result.claim == "COVID vaccines contain microchips."
    assert result.verification is not None
    assert result.verification.status in set(VerificationStatus)
    # Evidence should have been extracted and classified into buckets.
    total_evidence = (
        len(result.verification.supporting)
        + len(result.verification.contradicting)
        + len(result.verification.neutral)
    )
    assert total_evidence >= 1
    # Explanation is produced by the rule-based fallback (NoOp provider).
    assert result.explanation is not None
    assert result.explanation.text
    # Citations come from real retrieved URLs only.
    assert all(citation.url.startswith("https://") for citation in result.citations)


def test_full_pipeline_no_evidence_returns_unverified() -> None:
    pipeline = RAGPipeline(
        retriever=Retriever(provider=EmptyRetrievalProvider()),
        explainer=Explainer(provider=NoOpLLMProvider()),
    )

    result = pipeline.run("An entirely unverifiable claim about the future.")

    assert result.verification.status is VerificationStatus.UNVERIFIED
    assert result.verification.supporting == []
    assert result.verification.contradicting == []
    assert result.explanation is not None


def test_pipeline_strips_and_validates_claim(full_pipeline: RAGPipeline) -> None:
    result = full_pipeline.run("  COVID vaccines contain microchips.  ")
    assert result.claim == "COVID vaccines contain microchips."

    with pytest.raises(ValueError, match="cannot be empty"):
        full_pipeline.run("   ")

    with pytest.raises(TypeError, match="must be a string"):
        full_pipeline.run(12345)  # type: ignore[arg-type]


def test_pipeline_rejects_overlong_claim(full_pipeline: RAGPipeline) -> None:
    with pytest.raises(ValueError, match="too long"):
        full_pipeline.run("x" * (MAX_CLAIM_LENGTH + 1))


def test_pipeline_retrieval_failure_propagates_cleanly() -> None:
    pipeline = RAGPipeline(
        retriever=Retriever(
            provider=FixtureRetrievalProvider(should_fail=True, failure_message="Search API down")
        ),
        explainer=Explainer(provider=NoOpLLMProvider()),
    )

    with pytest.raises(RetrievalError, match="Search API down"):
        pipeline.run("A claim that cannot be retrieved.")


def test_pipeline_propagates_unexpected_explainer_failure() -> None:
    """A totally broken explainer propagates its error for the API to handle safely.

    The built-in Explainer already falls back gracefully on LLM failures; a
    custom explainer that raises an unexpected error is not swallowed silently
    (the API layer converts it into a safe HTTP 500).
    """

    class FailingExplainer:
        def explain(self, claim, verification):  # type: ignore[no-untyped-def]
            raise RuntimeError("explainer exploded")

    pipeline = RAGPipeline(
        retriever=Retriever(provider=FixtureRetrievalProvider(_documents())),
        explainer=FailingExplainer(),  # type: ignore[arg-type]
    )

    with pytest.raises(RuntimeError, match="explainer exploded"):
        pipeline.run("COVID vaccines contain microchips.")
