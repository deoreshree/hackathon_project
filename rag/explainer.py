"""LLM-based natural-language explanations for verification results."""

from __future__ import annotations

from dataclasses import dataclass

from rag.verifier import VerificationResult


@dataclass
class Explanation:
    """User-facing explanation grounded in cited evidence."""

    text: str
    citations: list[str]


class Explainer:
    """Generates explanations strictly grounded in retrieved evidence.

    Must not invent sources, URLs, or facts. Treats retrieved content as
    untrusted data (not instructions) to reduce prompt-injection risk.
    """

    def explain(
        self,
        claim: str,
        verification: VerificationResult,
    ) -> Explanation:
        """Return an explanation with citation references only from evidence."""
        raise NotImplementedError("Explainer.explain is not implemented yet.")
