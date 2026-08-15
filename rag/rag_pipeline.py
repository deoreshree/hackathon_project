"""Orchestrates retrieval, evidence extraction, verification, and explanation."""

from __future__ import annotations

from dataclasses import dataclass

from rag.evidence import EvidenceExtractor
from rag.explainer import Explainer, Explanation
from rag.retriever import Retriever
from rag.sources import SourceCitation, build_citations
from rag.verifier import VerificationResult, Verifier


@dataclass
class RAGResponse:
    """Integration-ready response for the backend API layer."""

    claim: str
    verification: VerificationResult
    explanation: Explanation | None
    citations: list[SourceCitation]


class RAGPipeline:
    """End-to-end RAG pipeline entry point for backend integration."""

    def __init__(
        self,
        retriever: Retriever | None = None,
        evidence_extractor: EvidenceExtractor | None = None,
        verifier: Verifier | None = None,
        explainer: Explainer | None = None,
    ) -> None:
        self.retriever = retriever or Retriever()
        self.evidence_extractor = evidence_extractor or EvidenceExtractor()
        self.verifier = verifier or Verifier()
        self.explainer = explainer or Explainer()

    def run(self, claim: str) -> RAGResponse:
        """Run the full RAG workflow for a single claim or news snippet."""
        raise NotImplementedError("RAGPipeline.run is not implemented yet.")
