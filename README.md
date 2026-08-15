# AI-Powered Fake News Detector — RAG Module (Member 2)

Retrieval-Augmented Generation (RAG) and evidence layer for the hackathon project.
This module retrieves real sources, extracts supporting/contradicting evidence,
returns verification status, and produces grounded LLM explanations.

**Scope:** RAG, evidence, citations, explainer, fact-check chatbot API hooks.  
**Out of scope:** Frontend, primary ML fake-news classifier.

## Safety rules

- Never invent evidence, sources, URLs, or citations.
- Return `UNVERIFIED` when reliable evidence is insufficient.
- Treat retrieved webpage content as **data**, not instructions (prompt-injection mitigation).
- Keep API keys in `.env` (see `.env.example`).

## Project layout

```
rag/
├── models.py         # Pydantic data models (RetrievedDocument, etc.)
├── providers.py      # Pluggable search backends (Tavily, Serper, empty, fixture)
├── retriever.py      # Retriever entry point
├── evidence.py       # Extract & label supporting vs contradicting snippets
├── verifier.py       # Aggregate evidence into verification status
├── explainer.py      # LLM explanations grounded in evidence
├── prompts.py        # Shared prompt templates & guardrails
├── sources.py        # Source config, priority ranking, citations
└── rag_pipeline.py   # Orchestration + integration-ready response model
tests/                # Unit tests
```

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
copy .env.example .env
```

## Retrieval module (Step 2)

### What it does

Given a user's news claim, the retriever searches the web (when configured) and returns
structured documents that can later be used as evidence. Results are ranked to prefer
sources explicitly marked as **authoritative** in configuration (e.g. Snopes, PolitiFact).

If no API key is configured, the retriever returns an **empty list** — it never fabricates
URLs or article text.

### Input

| Parameter | Type | Description |
|-----------|------|-------------|
| `query` | `str` | User claim / news text (required, non-empty) |
| `top_k` | `int` | Maximum number of documents to return (default: `5`) |

```python
from rag.retriever import Retriever

retriever = Retriever()
documents = retriever.retrieve("Vaccines contain microchips.", top_k=5)
```

For tests or custom wiring, inject a provider explicitly:

```python
from rag.providers import FixtureRetrievalProvider
from rag.retriever import Retriever

retriever = Retriever(provider=FixtureRetrievalProvider(documents=[...]))
```

### Output

Each item is a `RetrievedDocument`:

```json
{
  "title": "Fact-check headline",
  "url": "https://www.politifact.com/factchecks/example/",
  "source": "PolitiFact",
  "content": "Snippet or summary returned by the search API.",
  "relevance_score": 0.82,
  "is_authoritative": true
}
```

- `is_authoritative` is `true` **only** when the URL matches a source entry with `authoritative=True` in `rag/sources.py`.
- Unknown domains get `is_authoritative=false` even if they rank highly in search.

### Configuration

Set variables in `.env`:

| Variable | Purpose |
|----------|---------|
| `RETRIEVAL_PROVIDER` | `tavily`, `serper`, or `empty` (optional; auto-detects from keys) |
| `TAVILY_API_KEY` | Enables [Tavily](https://tavily.com) search |
| `SERPER_API_KEY` | Enables [Serper](https://serper.dev) Google search |

**Auto-selection order** when `RETRIEVAL_PROVIDER` is unset:

1. Tavily if `TAVILY_API_KEY` is set
2. Else Serper if `SERPER_API_KEY` is set
3. Else empty provider (returns `[]`)

Customize trusted sources by passing a list of `SourceEntry` to `Retriever(source_config=[...])`
or editing `DEFAULT_SOURCE_ENTRIES` in `rag/sources.py`.

### Retrieval flow

```
User claim
    → Retriever.retrieve()
        → RetrievalProvider.search()   # Tavily / Serper / empty / fixture
        → enrich_document()          # map URL → configured source name + authority flag
        → rank_documents()           # authoritative + priority + relevance score
    → list[RetrievedDocument]
```

## Evidence Extraction (Step 3)

### What it does

Given a user claim and the documents returned by the retriever, the evidence extractor
identifies the most relevant passages from **real retrieved content only**. It never
invents facts, sources, or URLs.

### Flow

```
Claim
    → Retrieved Documents
    → Relevant Passages (sentence/chunk split, keyword overlap scoring)
    → Ranked Evidence (deduplicated, capped at max_evidence)
```

### Input

| Parameter | Type | Description |
|-----------|------|-------------|
| `claim` | `str` | Original user claim |
| `documents` | `list[RetrievedDocument]` | Output from Step 2 retriever |
| `max_evidence` | `int` | Optional override (default: `5`) |

```python
from rag.evidence import EvidenceExtractor
from rag.retriever import Retriever

retriever = Retriever()
extractor = EvidenceExtractor(max_evidence=5)

documents = retriever.retrieve("COVID vaccines contain microchips.")
evidence = extractor.extract("COVID vaccines contain microchips.", documents)
```

### Output — `EvidenceItem`

```json
{
  "text": "Exact or faithfully extracted relevant passage from the document.",
  "source": "PolitiFact",
  "url": "https://www.politifact.com/factchecks/example/",
  "title": "Original document title",
  "relevance_score": 0.72
}
```

- `relevance_score` combines keyword overlap with the document's retrieval score when available.
- If no passage is relevant enough, returns `[]` instead of guessing.
- Empty claim, missing content, or duplicate URLs are handled safely without crashing.

### Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_evidence` | `5` | Maximum evidence items returned |
| `min_relevance` | `0.15` | Minimum score to include a passage |
| `max_passage_chars` | `500` | Max length of an extracted passage |
| `max_passages_per_document` | `2` | Limit passages taken from one source |

## Run tests

Tests use fixtures and do **not** require a real API key:

```bash
pytest
pytest tests/test_retriever.py -v
pytest tests/test_evidence.py -v
```

## Status

| Module | Status |
|--------|--------|
| Retrieval | Implemented |
| Evidence extraction | Implemented |
| Verification | Not started |
| LLM explanation | Not started |
| Full RAG pipeline | Not started |
