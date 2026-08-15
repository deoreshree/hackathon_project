"""Verification verdict logic based on collected evidence."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from rag.models import EvidenceItem


class VerificationStatus(str, Enum):
    """High-level fact-check outcome."""

    VERIFIED = "verified"
    REFUTED = "refuted"
    MIXED = "mixed"
    UNVERIFIED = "unverified"


@dataclass
class VerificationResult:
    """Structured verification output for downstream API consumers."""

    status: VerificationStatus
    supporting: list[EvidenceItem]
    contradicting: list[EvidenceItem]
    neutral: list[EvidenceItem]
    summary: str | None = None


class Verifier:
    """Aggregates evidence into a verification status.

    Returns UNVERIFIED when reliable evidence is insufficient.
    """

    def verify(
        self,
        claim: str,
        evidence: list[EvidenceItem],
    ) -> VerificationResult:
        """Produce a verification result from extracted evidence."""
        raise NotImplementedError("Verifier.verify is not implemented yet.")
