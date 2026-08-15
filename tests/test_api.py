"""API tests — Step 9 Part A.

Covers the HTTP surface: health, valid requests, and every malformed-input
class the backend must reject safely. External services (retrieval, LLM)
are mocked so tests run offline with no API keys.

Also covers rate-limit (HTTP 429) and CORS behavior at the HTTP layer.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from backend.main import app, chat_service, pipeline
from rag.explainer import Explanation
from rag.models import EvidenceItem
from rag.rag_pipeline import RAGResponse
from rag.sources import SourceCitation
from rag.verifier import VerificationResult, VerificationStatus

MAX_CLAIM_LENGTH = 5000
MAX_MESSAGE_LENGTH = 5000


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_backend_state() -> None:
    """Keep rate-limit and session state isolated between tests."""
    chat_service._sessions.clear()
    app.state.rate_limiter.reset()
    yield
    chat_service._sessions.clear()
    app.state.rate_limiter.reset()


@pytest.fixture
def sample_rag_result() -> RAGResponse:
    contradicting = EvidenceItem(
        text="India has never won the FIFA World Cup, according to official records.",
        source="Snopes",
        url="https://www.snopes.com/fact-check/india-world-cup",
        title="India World Cup claim",
        relevance_score=0.88,
    )
    verification = VerificationResult(
        status=VerificationStatus.LIKELY_FALSE,
        supporting=[],
        contradicting=[contradicting],
        neutral=[],
        summary="Evidence contradicts the claim.",
    )
    explanation = Explanation(
        text="The claim is likely false because India has not won the 2026 FIFA World Cup.",
        citations=[contradicting.url],
    )
    return RAGResponse(
        claim="India won the 2026 FIFA World Cup.",
        verification=verification,
        explanation=explanation,
        citations=[SourceCitation(url=contradicting.url, title=contradicting.title)],
    )


# ---------------------------------------------------------------------------
# 1. Health endpoint
# ---------------------------------------------------------------------------


def test_health_endpoint(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "fact-checking-api"


# ---------------------------------------------------------------------------
# 2. Valid fact-check request
# ---------------------------------------------------------------------------


def test_valid_fact_check_request(
    client: TestClient,
    sample_rag_result: RAGResponse,
    monkeypatch,
) -> None:
    monkeypatch.setattr(pipeline, "run", MagicMock(return_value=sample_rag_result))

    response = client.post(
        "/api/fact-check",
        json={"claim": "India won the 2026 FIFA World Cup."},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["claim"] == "India won the 2026 FIFA World Cup."
    assert data["verdict"] == "CONTRADICTED"
    assert isinstance(data["confidence"], float)
    assert data["explanation"]
    assert isinstance(data["evidence"], list)
    assert isinstance(data["sources"], list)


# ---------------------------------------------------------------------------
# 3. Valid chatbot request
# ---------------------------------------------------------------------------


def test_valid_chat_request(
    client: TestClient,
    sample_rag_result: RAGResponse,
    monkeypatch,
) -> None:
    monkeypatch.setattr(pipeline, "run", MagicMock(return_value=sample_rag_result))

    response = client.post("/chat", json={"message": "India won the 2026 FIFA World Cup."})
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "India won the 2026 FIFA World Cup."
    assert data["verdict"] == "CONTRADICTED"
    assert data["session_id"]


# ---------------------------------------------------------------------------
# 4. Empty request
# ---------------------------------------------------------------------------


def test_empty_body_returns_422(client: TestClient) -> None:
    response = client.post("/api/fact-check", json={})
    assert response.status_code == 422


def test_empty_claim_returns_422(client: TestClient) -> None:
    response = client.post("/api/fact-check", json={"claim": "   "})
    assert response.status_code == 422


def test_empty_chat_message_returns_422(client: TestClient) -> None:
    response = client.post("/chat", json={"message": " \t "})
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# 5. Missing required fields
# ---------------------------------------------------------------------------


def test_fact_check_missing_claim_returns_422(client: TestClient) -> None:
    response = client.post("/api/fact-check", json={"other": "value"})
    assert response.status_code == 422


def test_chat_missing_message_returns_422(client: TestClient) -> None:
    response = client.post("/chat", json={"session_id": "abc"})
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# 6. Invalid JSON
# ---------------------------------------------------------------------------


def test_invalid_json_returns_422(client: TestClient) -> None:
    response = client.post(
        "/api/fact-check",
        content="{not-valid-json",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422


def test_invalid_json_chat_returns_422(client: TestClient) -> None:
    response = client.post(
        "/chat",
        content="[1, 2, 3]",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# 7. Excessively long input
# ---------------------------------------------------------------------------


def test_excessively_long_claim_returns_422(client: TestClient) -> None:
    response = client.post(
        "/api/fact-check",
        json={"claim": "x" * (MAX_CLAIM_LENGTH + 1)},
    )
    assert response.status_code == 422


def test_excessively_long_chat_message_returns_422(client: TestClient) -> None:
    response = client.post(
        "/chat",
        json={"message": "y" * (MAX_MESSAGE_LENGTH + 1)},
    )
    assert response.status_code == 422


def test_long_session_id_returns_422(client: TestClient) -> None:
    response = client.post(
        "/chat",
        json={"message": "Hello", "session_id": "s" * 129},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# 8. Invalid data types
# ---------------------------------------------------------------------------


def test_claim_with_wrong_type_returns_422(client: TestClient) -> None:
    response = client.post("/api/fact-check", json={"claim": 12345})
    assert response.status_code == 422


def test_chat_message_with_wrong_type_returns_422(client: TestClient) -> None:
    response = client.post("/chat", json={"message": ["not", "a", "string"]})
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# 9. Internal service failure
# ---------------------------------------------------------------------------


def test_internal_service_failure_returns_500(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(pipeline, "run", MagicMock(side_effect=RuntimeError("boom")))

    response = client.post("/api/fact-check", json={"claim": "Some claim to check."})
    assert response.status_code == 500


def test_chat_internal_failure_returns_500(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(pipeline, "run", MagicMock(side_effect=RuntimeError("boom")))

    response = client.post("/chat", json={"message": "Some claim to check."})
    assert response.status_code == 500


# ---------------------------------------------------------------------------
# 10. Safe error responses — no internal details leaked
# ---------------------------------------------------------------------------


def test_500_error_does_not_leak_exception_details(
    client: TestClient,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        pipeline,
        "run",
        MagicMock(side_effect=RuntimeError("secret-internal-detail-xyz")),
    )

    response = client.post("/api/fact-check", json={"claim": "Check this claim."})
    assert response.status_code == 500
    detail = response.json()["detail"]
    assert "secret-internal-detail-xyz" not in detail
    assert "Traceback" not in detail
    assert "RuntimeError" not in detail


def test_chat_500_error_uses_safe_message(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(
        pipeline,
        "run",
        MagicMock(side_effect=RuntimeError("sensitive-internal-value")),
    )

    response = client.post("/chat", json={"message": "Check this claim."})
    assert response.status_code == 500
    assert "sensitive-internal-value" not in response.json()["detail"]
    assert "Chatbot failed" in response.json()["detail"]


def test_validation_error_does_not_echo_input(client: TestClient) -> None:
    long_payload = "a" * (MAX_CLAIM_LENGTH + 1)
    response = client.post("/api/fact-check", json={"claim": long_payload})
    assert response.status_code == 422
    body = response.text
    assert long_payload not in body
    assert "Traceback" not in body


# ---------------------------------------------------------------------------
# Rate-limit behavior (HTTP 429)
# ---------------------------------------------------------------------------


def sample_rag_result_factory() -> RAGResponse:
    neutral = EvidenceItem(
        text="Officials met to discuss tournament logistics.",
        source="Reuters",
        url="https://www.reuters.com/sports/tournament-logistics",
        title="Tournament update",
        relevance_score=0.5,
    )
    verification = VerificationResult(
        status=VerificationStatus.UNVERIFIED,
        supporting=[],
        contradicting=[],
        neutral=[neutral],
        summary="No conclusive evidence.",
    )
    return RAGResponse(
        claim="Claim",
        verification=verification,
        explanation=None,
        citations=[],
    )


def test_rate_limit_returns_429_when_exceeded(client: TestClient, monkeypatch) -> None:
    limiter = app.state.rate_limiter
    original_max = limiter.max_requests
    try:
        limiter.max_requests = 2
        limiter.reset()

        monkeypatch.setattr(pipeline, "run", MagicMock(return_value=sample_rag_result_factory()))

        first = client.post("/api/fact-check", json={"claim": "Claim number one."})
        second = client.post("/api/fact-check", json={"claim": "Claim number two."})
        third = client.post("/api/fact-check", json={"claim": "Claim number three."})

        assert first.status_code == 200
        assert second.status_code == 200
        assert third.status_code == 429
        assert "Too many requests" in third.json()["detail"]
    finally:
        limiter.max_requests = original_max
        limiter.reset()


# ---------------------------------------------------------------------------
# CORS behavior
# ---------------------------------------------------------------------------


def test_cors_headers_present_for_cross_origin(client: TestClient) -> None:
    response = client.get("/health", headers={"Origin": "http://localhost:3000"})
    assert response.headers.get("access-control-allow-origin") == "*"


def test_cors_does_not_enable_credentials(client: TestClient) -> None:
    response = client.get("/health", headers={"Origin": "http://localhost:3000"})
    assert "access-control-allow-credentials" not in response.headers
