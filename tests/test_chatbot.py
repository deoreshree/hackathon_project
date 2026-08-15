"""Tests for the fact-checking chatbot API and chat service."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from backend.chat_service import ChatService
from backend.main import app, chat_service, pipeline
from backend.response_builder import build_fact_check_response
from backend.schemas import EvidenceResponse, FactCheckResponse, SourceResponse
from rag.explainer import Explanation
from rag.models import EvidenceItem
from rag.rag_pipeline import RAGResponse
from rag.verifier import VerificationResult, VerificationStatus


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def sample_rag_result() -> RAGResponse:
    supporting = EvidenceItem(
        text="FIFA records show the 2026 World Cup has not been awarded to India.",
        source="Reuters",
        url="https://www.reuters.com/sports/fifa-2026",
        title="FIFA 2026 update",
        relevance_score=0.91,
    )
    contradicting = EvidenceItem(
        text="India has never won the FIFA World Cup.",
        source="Snopes",
        url="https://www.snopes.com/fact-check/india-world-cup",
        title="India World Cup claim",
        relevance_score=0.88,
    )
    verification = VerificationResult(
        status=VerificationStatus.LIKELY_FALSE,
        supporting=[],
        contradicting=[contradicting],
        neutral=[supporting],
        summary="Evidence contradicts the claim.",
    )
    explanation = Explanation(
        text="The claim is likely false because India has not won the 2026 FIFA World Cup.",
        citations=[contradicting.url],
    )
    from rag.sources import SourceCitation

    citations = [
        SourceCitation(url=contradicting.url, title=contradicting.title),
        SourceCitation(url=supporting.url, title=supporting.title),
    ]
    return RAGResponse(
        claim="India won the 2026 FIFA World Cup.",
        verification=verification,
        explanation=explanation,
        citations=citations,
    )


@pytest.fixture(autouse=True)
def reset_chat_sessions() -> None:
    chat_service._sessions.clear()
    yield
    chat_service._sessions.clear()


def test_chat_valid_claim(client: TestClient, sample_rag_result: RAGResponse, monkeypatch) -> None:
    monkeypatch.setattr(pipeline, "run", MagicMock(return_value=sample_rag_result))

    response = client.post(
        "/chat",
        json={"message": "India won the 2026 FIFA World Cup."},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "India won the 2026 FIFA World Cup."
    assert data["verdict"] == "CONTRADICTED"
    assert data["confidence"] >= 0.0
    assert "likely false" in data["answer"].lower()
    assert data["session_id"]
    assert data["is_follow_up"] is False


def test_chat_empty_message_returns_400(client: TestClient) -> None:
    response = client.post("/chat", json={"message": "   "})
    assert response.status_code == 422 or response.status_code == 400


def test_chat_backend_error_returns_500(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(pipeline, "run", MagicMock(side_effect=RuntimeError("RAG failed")))

    response = client.post("/chat", json={"message": "Test claim about sports."})
    assert response.status_code == 500
    assert "Chatbot failed" in response.json()["detail"]


def test_chat_response_contains_verdict(client: TestClient, sample_rag_result: RAGResponse, monkeypatch) -> None:
    monkeypatch.setattr(pipeline, "run", MagicMock(return_value=sample_rag_result))

    data = client.post("/chat", json={"message": "India won the 2026 FIFA World Cup."}).json()
    assert data["verdict"] in {"SUPPORTED", "CONTRADICTED", "MIXED", "UNVERIFIED"}


def test_chat_response_contains_grounded_explanation(
    client: TestClient,
    sample_rag_result: RAGResponse,
    monkeypatch,
) -> None:
    monkeypatch.setattr(pipeline, "run", MagicMock(return_value=sample_rag_result))

    data = client.post("/chat", json={"message": "India won the 2026 FIFA World Cup."}).json()
    assert data["explanation"]
    assert "2026" in data["answer"] or "false" in data["answer"].lower()


def test_chat_response_returns_evidence_buckets(
    client: TestClient,
    sample_rag_result: RAGResponse,
    monkeypatch,
) -> None:
    monkeypatch.setattr(pipeline, "run", MagicMock(return_value=sample_rag_result))

    data = client.post("/chat", json={"message": "India won the 2026 FIFA World Cup."}).json()
    assert len(data["contradicting_evidence"]) >= 1
    assert data["contradicting_evidence"][0]["url"].startswith("https://")
    assert data["sources"]


def test_chat_follow_up_uses_session_without_rerun(
    client: TestClient,
    sample_rag_result: RAGResponse,
    monkeypatch,
) -> None:
    mock_run = MagicMock(return_value=sample_rag_result)
    monkeypatch.setattr(pipeline, "run", mock_run)

    first = client.post("/chat", json={"message": "India won the 2026 FIFA World Cup."}).json()
    second = client.post(
        "/chat",
        json={"message": "Why?", "session_id": first["session_id"]},
    ).json()

    assert mock_run.call_count == 1
    assert second["is_follow_up"] is True
    assert second["verdict"] == first["verdict"]
    assert "evidence" in second["answer"].lower()


def test_chat_service_follow_up_without_session_runs_pipeline(sample_rag_result: RAGResponse) -> None:
    mock_pipeline = MagicMock()
    mock_pipeline.run.return_value = sample_rag_result
    service = ChatService(mock_pipeline, build_response=build_fact_check_response)

    first = service.handle_message("India won the 2026 FIFA World Cup.")
    follow_up = service.handle_message("Why?", first.session_id)

    assert mock_pipeline.run.call_count == 1
    assert follow_up.is_follow_up is True


def test_fact_check_endpoint_still_works(client: TestClient, sample_rag_result: RAGResponse, monkeypatch) -> None:
    monkeypatch.setattr(pipeline, "run", MagicMock(return_value=sample_rag_result))

    response = client.post("/api/fact-check", json={"claim": "India won the 2026 FIFA World Cup."})
    assert response.status_code == 200
    data = response.json()
    assert data["claim"] == "India won the 2026 FIFA World Cup."
    assert data["verdict"] == "CONTRADICTED"


def test_chat_page_served(client: TestClient) -> None:
    response = client.get("/chat")
    assert response.status_code == 200
    assert "Fact-Checking Chatbot" in response.text


def test_chat_long_message_returns_422(client: TestClient) -> None:
    response = client.post("/chat", json={"message": "a" * 5001})
    assert response.status_code == 422


def test_chat_invalid_request_missing_message_returns_422(client: TestClient) -> None:
    response = client.post("/chat", json={})
    assert response.status_code == 422


def test_chat_invalid_request_wrong_type_returns_422(client: TestClient) -> None:
    response = client.post("/chat", json={"message": 42})
    assert response.status_code == 422


def test_chat_invalid_json_returns_422(client: TestClient) -> None:
    response = client.post(
        "/chat",
        content="{malformed",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422


def test_chat_sources_returned_when_available(
    client: TestClient,
    sample_rag_result: RAGResponse,
    monkeypatch,
) -> None:
    monkeypatch.setattr(pipeline, "run", MagicMock(return_value=sample_rag_result))

    data = client.post("/chat", json={"message": "India won the 2026 FIFA World Cup."}).json()
    assert data["sources"]
    assert all(source["url"].startswith("https://") for source in data["sources"])
