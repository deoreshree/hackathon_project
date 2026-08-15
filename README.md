# AI-Powered Fake News Detector

A hackathon-ready fact-checking application. Users submit a news claim; the system
retrieves real web evidence, extracts supporting/contradicting/neutral passages,
classifies them, and produces a **grounded verdict and LLM explanation** backed by
citations. A chat interface wraps the whole pipeline for a live demo.

## Overview

The application answers one question per claim: *is there reliable, retrievable
evidence that supports, contradicts, or is neutral toward this claim?* It never
invents evidence — when evidence is insufficient it says **UNVERIFIED** instead
of guessing. The pipeline is deterministic and testable offline (no API keys
required for tests), and can be upgraded with live web-search and LLM keys for
the demo.

## Key Features

- **Claim verification** — verdicts: `SUPPORTED`, `CONTRADICTED`, `MIXED`, `UNVERIFIED`
- **Web / evidence retrieval** — Tavily, Serper, or offline fixture providers
- **Evidence extraction** — relevant passages extracted from real retrieved content
- **Supporting / contradicting / neutral classification** — deterministic, keyword-based
- **RAG pipeline** — retrieval → extraction → verification → explanation → citations
- **Grounded LLM explanation** — evidence-only prompts + output validation (no hallucinations)
- **Fact-checking chatbot** — chat UI with follow-up support (`Why?`, `What evidence?`)
- **API / backend** — FastAPI with OpenAPI docs
- **Security** — input validation, safe error handling, rate limiting, prompt-injection guards
- **Automated testing** — offline, mocked, deterministic (156 tests)

## Architecture

```
User
  → Chatbot (static/ UI)
    → FastAPI backend (backend/main.py)
      → RAG Pipeline (rag/rag_pipeline.py)
        → Retrieval (rag/retriever.py + providers)
        → Evidence extraction (rag/evidence.py)
        → Evidence classification (rag/verifier.py)
        → Verification status (rag/verifier.py)
        → Grounded LLM explanation (rag/explainer.py)
        → Source citations (rag/sources.py)
      → API response (backend/schemas.py, response_builder.py)
    → Chatbot response (backend/chat_service.py)
```

## Tech Stack

- **Python 3** (type-hinted, `from __future__ import annotations`)
- **FastAPI + Uvicorn** — REST API and server
- **Pydantic v2** — request/response validation
- **httpx** — outbound calls to search/LLM providers
- **python-dotenv** — environment configuration
- **pytest** — automated tests
- **Vanilla HTML/CSS/JS** — chatbot demo UI (no frontend framework)

## Project Structure

```
backend/
├── main.py            # FastAPI app: routes, CORS, error handling, rate limiting
├── schemas.py         # Pydantic request/response models + input validation
├── chat_service.py    # Chatbot sessions + follow-up logic
├── response_builder.py# RAG output → API response mapping
└── rate_limit.py      # Lightweight in-memory rate limiter
rag/
├── models.py          # Pydantic data models (RetrievedDocument, EvidenceItem)
├── providers.py       # Search backends (Tavily, Serper, empty, fixture)
├── retriever.py       # Retrieval entry point
├── evidence.py        # Evidence extraction
├── verifier.py        # Stance classification + verification status
├── explainer.py       # LLM + rule-based explanations
├── prompts.py         # Prompt templates + injection guardrails
├── sources.py         # Source config, ranking, citations
└── rag_pipeline.py    # End-to-end orchestration
static/
├── index.html         # Chat UI
├── app.js             # Chat client logic
└── style.css          # Chat UI styling
tests/                 # pytest suite (offline, mocked)
requirements.txt
.env.example           # Placeholder environment template (no real keys)
```

## Installation

From a terminal in the project root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # Windows PowerShell
pip install -r requirements.txt
copy .env.example .env            # then fill in your API keys (optional)
```

Linux/macOS activation: `source .venv/bin/activate` and `cp .env.example .env`.

## Environment Variables

Copy `.env.example` to `.env` and fill in values. **Never commit `.env`** — it is
Git-ignored. Placeholder-only values live in `.env.example`:

| Variable | Purpose |
|----------|---------|
| `RETRIEVAL_PROVIDER` | `tavily`, `serper`, or `empty` (auto-detected if unset) |
| `TAVILY_API_KEY` | Enables live web search via Tavily |
| `SERPER_API_KEY` | Enables live web search via Serper |
| `OPENAI_API_KEY` | Enables LLM explanations (OpenAI) |
| `GROQ_API_KEY` | Enables LLM explanations (Groq, free tier) |
| `RATE_LIMIT_ENABLED` / `RATE_LIMIT_MAX_REQUESTS` / `RATE_LIMIT_WINDOW_SECONDS` | Rate limiting (default 120 req/min/IP) |
| `CORS_ORIGINS` | Comma-separated allowed origins (default `*`) |
| `LOG_LEVEL` | Logging level |

With no keys configured the app still runs: retrieval returns no results and
explanations use the deterministic rule-based fallback (everything becomes
`UNVERIFIED`). Add keys for the full live demo.

## Running the Application

```powershell
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Then open:

- Chat UI: http://127.0.0.1:8000/chat
- API docs (Swagger/OpenAPI): http://127.0.0.1:8000/docs

## API Documentation

FastAPI auto-generates interactive docs at **`/docs`** (Swagger UI) and the raw
OpenAPI schema at **`/openapi.json`**.

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/health` | Health check |
| `GET` | `/` | API info |
| `GET` | `/chat` | Chat UI (HTML) |
| `POST` | `/api/fact-check` | Direct fact-check of a `claim` |
| `POST` | `/chat` | Chatbot fact-check (`message` + optional `session_id`) |

Example request:

```bash
curl -X POST http://127.0.0.1:8000/api/fact-check \
  -H "Content-Type: application/json" \
  -d '{"claim": "COVID vaccines contain microchips for tracking people."}'
```

## Running Tests

The suite runs fully offline — external services are mocked, no API keys needed:

```powershell
pytest -q
```

## Example

Claim: **"COVID vaccines contain microchips for tracking people."**  
Verdict: **CONTRADICTED** — retrieved evidence (CNBC, FactCheck.org, Mayo Clinic)
explicitly debunks the microchip claim. The response includes confidence, a
grounded explanation, contradicting evidence passages, and source links.

## Security

Implemented in Step 9:

- **Input validation** — Pydantic schemas strip and reject blank input; caps of
  5,000 chars for claims/messages, 128 for session ids; invalid JSON, wrong
  types, and missing fields return `422`.
- **Safe error handling** — internal exceptions are logged but never exposed;
  clients get generic `500` messages; no stack traces, paths, or keys leak.
- **Secret management** — API keys come only from `.env` (Git-ignored);
  `.env.example` holds placeholders; the frontend never sees keys.
- **Prompt-injection protection** — claims and retrieved evidence are labeled
  as untrusted DATA; the system prompt forbids revealing instructions, keys,
  or secrets; LLM source URLs are validated against real evidence.
- **Rate limiting** — lightweight in-memory limiter (120 req/min/IP) returns `429`.
- **CORS** — configurable origins via `CORS_ORIGINS`; credentials disabled.

## Safety rules

- Never invent evidence, sources, URLs, or citations.
- Return `UNVERIFIED` when reliable evidence is insufficient.
- Treat retrieved webpage content as **data**, not instructions (prompt-injection mitigation).
- Keep API keys in `.env` (see `.env.example`).

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

## Evidence Verification (Step 4)

### What it does

Classifies each `EvidenceItem` as **SUPPORTING**, **CONTRADICTING**, or **NEUTRAL**
toward the claim, then aggregates those stances (weighted by relevance score and
source authority) into a single `VerificationStatus`:

| Status | Meaning |
|--------|---------|
| `LIKELY_TRUE` | Reliable evidence generally supports the claim |
| `LIKELY_FALSE` | Reliable evidence generally contradicts the claim |
| `MIXED` | Meaningful evidence exists on both sides |
| `UNVERIFIED` | Insufficient reliable evidence to conclude |

```python
from rag.verifier import Verifier

verifier = Verifier()
result = verifier.verify(claim, evidence)
print(result.status)        # VerificationStatus.LIKELY_TRUE
print(result.supporting)    # list[EvidenceItem]
print(result.contradicting) # list[EvidenceItem]
print(result.summary)       # human-readable string
```

Classification is **purely deterministic and keyword-based** — no LLM API
key is needed for this step. Known authoritative sources (Snopes, PolitiFact,
Reuters, etc.) receive an authority weight bonus.

---

## LLM Evidence Explanation (Step 5)

### What it does

Takes the claim, all evidence buckets, and the `VerificationResult` from Step 4,
then calls an LLM to produce a **structured, grounded explanation**.

The LLM is given **only** the retrieved evidence — not the open internet.
All hallucination guardrails are enforced at the prompt level and again
at the output-validation level.

### Explanation flow

```
Claim
  → Retrieved Evidence (Step 2)
  → Extracted Passages (Step 3)
  → Verification Status (Step 4)
  → LLM (system prompt with strict evidence-only rules)
  → Grounded Explanation
```

### Output — `ExplanationResult`

```json
{
  "verdict":       "LIKELY_TRUE | LIKELY_FALSE | MIXED | UNVERIFIED",
  "explanation":   "1-3 sentence explanation grounded in the supplied evidence.",
  "key_evidence":  ["Direct quote or paraphrase from evidence item 1", "..."],
  "sources":       [
    {"title": "Article title", "url": "https://...", "source": "Publisher"}
  ],
  "llm_used":      true
}
```

- `key_evidence` and `sources` are populated **only** from real retrieved items.
- `llm_used` is `false` when the LLM is unavailable or fails — the rule-based
  fallback produces the same structured output without any network call.

### Safety / reliability rules

| Rule | Implementation |
|------|----------------|
| No invented facts | LLM system prompt explicitly forbids using its own knowledge |
| No invented URLs | LLM output sources are cross-checked against real evidence URLs |
| No invented source names | Same URL-validation step strips hallucinated sources |
| Prompt injection mitigation | Evidence sections are labelled as "DATA" |
| LLM failure → fallback | Any error (network, bad JSON, timeout) falls back deterministically |
| Missing API key → fallback | `NoOpLLMProvider` triggers rule-based fallback, never crashes |

### Usage

```python
from rag.explainer import ExplanationGenerator
from rag.verifier import Verifier

verifier = Verifier()
verification = verifier.verify(claim, evidence)

generator = ExplanationGenerator()          # picks LLM from .env automatically
result = generator.generate(claim, verification)

print(result.verdict)      # "LIKELY_TRUE"
print(result.explanation)  # "Based on retrieved evidence..."
print(result.sources)      # [{"title": ..., "url": ..., "source": ...}]
```

### LLM provider configuration

| Variable | Provider | Model |
|----------|----------|-------|
| `OPENAI_API_KEY` | OpenAI | `gpt-4o-mini` |
| `GROQ_API_KEY` | Groq (free tier) | `llama-3.1-8b-instant` |
| *(neither set)* | Rule-based fallback | *(no network call)* |

Set `LLM_PROVIDER=openai` or `LLM_PROVIDER=groq` in `.env` to override
auto-detection.  The provider interface (`LLMProvider` ABC) makes it easy
to add Mistral, Anthropic, or any other backend later.

### How the LLM is grounded in evidence

1. **System prompt**: 9 explicit rules prohibit the model from using its own
   knowledge, inventing URLs, or fabricating citations. It is told to output
   `UNVERIFIED` when evidence is insufficient.

2. **User prompt**: Every piece of evidence is injected as labelled DATA blocks
   (`[S1]`, `[C1]`, `[N1]`, …). Only evidence from the retriever appears.

3. **Output validation**: After the LLM responds, `_validate_sources()` removes
   any source URL that was not in the original evidence list, preventing the
   model from slipping invented citations past the guardrails.

4. **JSON-only output**: `temperature=0.0` and a strict JSON schema in the
   prompt minimise free-form hallucination.

5. **Deterministic fallback**: The rule-based `_rule_based_explanation()` path
   produces a correct verdict from `VerificationResult` fields alone — so even
   if the LLM invents something, the fallback path never will.

---

## Run tests

Tests use fixtures and stubs and do **not** require a real API key:

```bash
pytest
pytest tests/test_retriever.py -v
pytest tests/test_evidence.py -v
pytest tests/test_verifier.py -v
pytest tests/test_explainer.py -v
pytest tests/test_chatbot.py -v
```

---

## Step 8 — Fact-Checking Chatbot

### How it works

The chatbot reuses the existing Step 6 `RAGPipeline` and Step 7 FastAPI backend.
A user sends a natural-language claim through `POST /chat`. The backend runs the
same retrieval → evidence → verification → explanation flow as `/api/fact-check`.

For short follow-up questions such as `"Why?"` or `"What evidence?"`, the chatbot
returns a follow-up answer from the **cached last fact-check result** in the session.
Conversation history does **not** override or replace retrieved evidence.

### API endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/chat` | Minimal chat UI |
| `POST` | `/chat` | Chatbot fact-check API |
| `POST` | `/api/fact-check` | Existing direct fact-check API |

### Request format

```json
{
  "message": "India won the 2026 FIFA World Cup.",
  "session_id": "optional-existing-session-id"
}
```

### Response format

```json
{
  "session_id": "f8b2c1a0-...",
  "message": "India won the 2026 FIFA World Cup.",
  "verdict": "CONTRADICTED",
  "confidence": 0.92,
  "answer": "The claim appears contradicted by the retrieved evidence. ...",
  "explanation": "The claim is likely false because ...",
  "supporting_evidence": [],
  "contradicting_evidence": [
    {
      "text": "India has never won the FIFA World Cup.",
      "source": "Snopes",
      "url": "https://www.snopes.com/fact-check/india-world-cup",
      "title": "India World Cup claim",
      "relevance_score": 0.88,
      "stance": "contradicting"
    }
  ],
  "neutral_evidence": [],
  "sources": [
    {
      "url": "https://www.snopes.com/fact-check/india-world-cup",
      "title": "India World Cup claim",
      "publisher": null
    }
  ],
  "is_follow_up": false
}
```

Verdict values follow the existing backend mapping:

- `SUPPORTED`
- `CONTRADICTED`
- `MIXED`
- `UNVERIFIED`

### Run the chatbot locally

From the project root:

```bash
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Then open:

- Chat UI: [http://127.0.0.1:8000/chat](http://127.0.0.1:8000/chat)
- API docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

Example request:

```bash
curl -X POST http://127.0.0.1:8000/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"message\": \"India won the 2026 FIFA World Cup.\"}"
```

### Frontend

A minimal demo UI lives in `static/`:

- `static/index.html`
- `static/app.js`
- `static/style.css`

It connects to `POST /chat`, shows verdict, evidence, sources, loading state, and errors.
No API keys are exposed in frontend code.

## Step 9 — Security + Testing

Security hardening and a comprehensive automated test suite covering Steps 1–9.

### Input validation

All user input is validated with the existing Pydantic schemas (`backend/schemas.py`):

- `claim` / `message` must be non-empty after stripping (whitespace-only input → 422).
- `claim` and `message` are capped at **5,000 characters**.
- `session_id` is capped at **128 characters** and stripped.
- The RAG pipeline (`rag/rag_pipeline.py`) independently rejects empty, non-string,
  and over-long (`> 5000` chars) claims, so direct pipeline calls are protected too.
- Invalid JSON, missing fields, and wrong data types return **HTTP 422** with a
  sanitized error body that never echoes back raw input values.

### API security

- **Safe error messages:** internal exceptions are logged server-side but clients
  only ever see generic messages (`"Fact-checking failed due to an internal error…"`).
  Stack traces, exception types, file paths, and message details are never exposed.
- **HTTP status codes:** `400` (bad input from the pipeline), `422` (validation),
  `429` (rate limited), `500` (internal failure).
- **CORS:** configurable via `CORS_ORIGINS` (comma-separated, default `*`).
  `allow_credentials` is `False` so `*` remains a valid, safe configuration.
- A catch-all exception handler guarantees no unhandled error ever leaks internals.

### Secret management

- API keys are read **only** from environment variables / `.env` — never hardcoded.
- `.env` is ignored by Git (`.gitignore` contains `.env`; `.env.*` except `.env.example`).
- `.env.example` contains **placeholder values only** (e.g. `TAVILY_API_KEY=your_tavily_api_key_here`).
- The frontend (`static/`) never receives or displays API keys.

### Prompt injection protection

- Claims and retrieved evidence are treated as **data**, not instructions:
  `rag/prompts.py` labels them `(DATA)` in the LLM prompt and explicitly forbids
  following embedded instructions ("ignore previous instructions", "reveal the
  API key", "disclose the system prompt", …).
- The system prompt instructs the LLM to never reveal its instructions, API keys,
  or secrets, and to judge only on supplied evidence.
- LLM output is validated: source URLs are cross-checked against the real evidence
  list, so fabricated citations are stripped (`rag/explainer.py`).
- If the LLM is unavailable or fails, a deterministic rule-based fallback produces
  the explanation — no external call, no hallucinated content.

### Rate limiting

A lightweight, in-memory sliding-window rate limiter (`backend/rate_limit.py`)
protects `POST /api/fact-check` and `POST /chat` (default **120 requests/min per IP**).
No external dependency — suitable for the hackathon demo. Configurable via env:

| Variable | Default | Purpose |
|----------|---------|---------|
| `RATE_LIMIT_ENABLED` | `true` | Set to `false` to disable |
| `RATE_LIMIT_MAX_REQUESTS` | `120` | Max requests per window |
| `RATE_LIMIT_WINDOW_SECONDS` | `60` | Sliding window length |

Exceeded limits return **HTTP 429** with a safe message.

### Error handling

| Case | Response |
|------|----------|
| Empty / whitespace-only input | `422` |
| Missing field / wrong type / invalid JSON | `422` |
| Over-long input | `422` |
| Pipeline input error (`ValueError`) | `400` |
| Rate limit exceeded | `429` |
| Internal / external service failure | `500` (safe message, no internals) |

External LLM/search failures never surface raw exception details to clients.

### Testing strategy

The suite uses **mocks and fixtures only** — it runs fully offline, deterministically,
and without any API keys. External services (DeepSeek/OpenAI/Groq LLM, Tavily/Serper
search, websites, network calls) are never contacted during tests.

Coverage:

| Area | Files |
|------|-------|
| API endpoints (health, valid, empty, missing fields, invalid JSON, long input, bad types, internal failure, safe errors, CORS, rate limit) | `tests/test_api.py` |
| Security (prompt injection, secret exposure, unsafe retrieved content, env handling, rate-limiter unit tests) | `tests/test_security.py` |
| RAG pipeline end-to-end + failure safety | `tests/test_rag_pipeline.py` |
| Chatbot (normal, empty, long, invalid, verdict/explanation/evidence/sources, follow-up) | `tests/test_chatbot.py` |
| Retrieval / evidence / verifier / explainer / sources (Steps 2–5) | `tests/test_retriever.py`, `tests/test_evidence.py`, `tests/test_verifier.py`, `tests/test_explainer.py`, `tests/test_sources.py` |

### How to run tests

```bash
pytest -q
```

Or run a single area:

```bash
pytest tests/test_api.py -v
pytest tests/test_security.py -v
```

---

## Status

| Module | Status |
|--------|--------|
| Retrieval (Step 2) | ✅ Implemented |
| Evidence extraction (Step 3) | ✅ Implemented |
| Evidence verification (Step 4) | ✅ Implemented |
| LLM explanation (Step 5) | ✅ Implemented |
| Full RAG pipeline (Step 6) | ✅ Implemented |
| Backend/API integration (Step 7) | ✅ Implemented |
| Fact-checking chatbot (Step 8) | ✅ Implemented |
| Security + Testing (Step 9) | ✅ Implemented |
| Final demo & release (Step 10) | ✅ Implemented |

---

## Limitations

This is a **hackathon demo, not a production fact-checker**. Please note:

- **Dependence on external evidence sources** — verdicts are only as good as the
  search results available at query time. If retrieval fails or returns nothing,
  the claim is marked `UNVERIFIED`.
- **LLM uncertainty** — LLM explanations can be imperfect. They are constrained
  to the supplied evidence, and fall back to deterministic rule-based text when
  the LLM is unavailable, but they are not a guarantee of truth.
- **Retrieval quality** — snippet-based retrieval can miss relevant sources or
  rank low-quality pages highly; source authority weighting is heuristic.
- **API availability** — live search/LLM features depend on external API keys
  and provider uptime. Without keys, the app runs in degraded (offline) mode.
- **No guaranteed truth in ambiguous cases** — `MIXED` and `UNVERIFIED` verdicts
  mean the system cannot confidently resolve the claim. Do not claim 100%
  accuracy; always verify important claims against primary sources.
- **In-memory rate limiting** — resets on restart and is single-process only.

## Future Improvements

- Train/apply a dedicated ML classifier for stance detection to replace the
  keyword heuristic.
- Add caching for repeated claims and persistent rate limiting.
- Support additional retrieval and LLM providers (e.g. DeepSeek, Mistral,
  Anthropic) through the existing provider interfaces.
- Add user authentication and per-user usage quotas.
- Improve evidence ranking with semantic embeddings (e.g. sentence-transformers).
