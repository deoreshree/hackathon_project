"""Extended tests for source configuration and citation helpers."""

import pytest

from rag.models import RetrievedDocument
from rag.models import EvidenceItem
from rag.sources import (
    build_citations,
    build_citations_from_items,
    extract_domain,
    match_source,
    normalize_url,
    rank_documents,
    resolve_source_metadata,
)


def test_normalize_url_strips_and_preserves_valid_url() -> None:
    assert normalize_url("  https://example.com/article  ") == "https://example.com/article"


def test_build_citations_deduplicates_urls() -> None:
    citations = build_citations(
        ["https://example.com/a", "https://example.com/a", "https://example.com/b"],
        ["A", "A duplicate", "B"],
    )
    assert len(citations) == 2
    assert citations[0].url == "https://example.com/a"
    assert citations[0].title == "A"


def test_extract_domain_removes_www() -> None:
    assert extract_domain("https://www.politifact.com/article") == "politifact.com"


def test_match_source_finds_configured_domain() -> None:
    from rag.sources import DEFAULT_SOURCE_ENTRIES

    matched = match_source(
        "https://www.snopes.com/fact-check/example/",
        list(DEFAULT_SOURCE_ENTRIES),
    )
    assert matched is not None
    assert matched.name == "Snopes"
    assert matched.authoritative is True


def test_resolve_source_metadata_unknown_domain_not_authoritative() -> None:
    from rag.sources import DEFAULT_SOURCE_ENTRIES

    name, authoritative, priority = resolve_source_metadata(
        "https://random-blog.example/post",
        list(DEFAULT_SOURCE_ENTRIES),
    )
    assert name == "random-blog.example"
    assert authoritative is False
    assert priority == 0


def test_rank_documents_does_not_mark_unknown_as_authoritative() -> None:
    doc = RetrievedDocument(
        title="Blog",
        url="https://unknown-site.example/post",
        source="unknown-site.example",
        content="Some content.",
        relevance_score=0.99,
    )
    ranked = rank_documents([doc])
    assert ranked[0].is_authoritative is False


def test_build_citations_from_evidence_items() -> None:
    items = [
        EvidenceItem(
            text="Passage one.",
            source="Snopes",
            url="https://www.snopes.com/fact-check/example",
            title="Snopes Check",
            relevance_score=0.8,
        ),
        EvidenceItem(
            text="Passage two (duplicate URL).",
            source="Snopes",
            url="https://www.snopes.com/fact-check/example",
            title="Snopes Check",
            relevance_score=0.6,
        ),
    ]

    citations = build_citations_from_items(items)

    assert len(citations) == 1
    assert citations[0].url == "https://www.snopes.com/fact-check/example"
    assert citations[0].title == "Snopes Check"
    assert citations[0].publisher == "Snopes"


def test_build_citations_from_items_skips_invalid_urls() -> None:
    items = [
        RetrievedDocument(
            title="Bad",
            url="not-a-url",
            source="x",
            content="Content.",
        ),
        RetrievedDocument(
            title="Good",
            url="https://example.com/article",
            source="example.com",
            content="Content.",
            relevance_score=0.5,
        ),
    ]

    citations = build_citations_from_items(items)

    assert len(citations) == 1
    assert citations[0].url == "https://example.com/article"


def test_build_citations_from_items_empty() -> None:
    assert build_citations_from_items([]) == []
