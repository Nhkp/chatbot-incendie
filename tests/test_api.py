from __future__ import annotations

from dataclasses import dataclass

from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from chatbot_incendie.api import _env_float, _env_int, _llm_api_keys, create_app
from chatbot_incendie.rag import SAFE_UNKNOWN_ANSWER, ChatAnswer, Citation


@dataclass(frozen=True)
class FakeChatService:
    answer: ChatAnswer

    def answer_question(self, question: str, top_k: int = 5) -> ChatAnswer:
        return self.answer


def test_health_endpoint() -> None:
    client = TestClient(create_app(service=_service()))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_endpoint_returns_answer_and_citations() -> None:
    client = TestClient(create_app(service=_service()))

    response = client.post("/chat", json={"question": "Quel est le risque ?", "top_k": 1})

    assert response.status_code == 200
    assert response.json() == {
        "answer": "Réponse sourcée [1].",
        "citations": [
            {
                "source_id": "meteo-des-forets-realtime",
                "title": "Meteo des forets 33",
                "document_url": "https://example.com/doc",
                "canonical_url": "https://example.com/canonical",
                "score": 0.91,
                "published_at": "2026-07-28T14:50:04+00:00",
                "collected_at": "2026-07-29T13:54:08+00:00",
            }
        ],
        "retrieved_count": 1,
        "model_name": "fake-llm",
    }


def test_chat_endpoint_rejects_blank_question() -> None:
    client = TestClient(create_app(service=_service()))

    response = client.post("/chat", json={"question": "   "})

    assert response.status_code == 422


def test_chat_endpoint_returns_safe_unknown_without_citations() -> None:
    client = TestClient(
        create_app(
            service=FakeChatService(
                ChatAnswer(
                    answer=SAFE_UNKNOWN_ANSWER,
                    citations=[],
                    retrieved_count=0,
                    model_name="fake-llm",
                )
            )
        )
    )

    response = client.post("/chat", json={"question": "Puis-je rentrer chez moi ?"})

    assert response.status_code == 200
    assert response.json()["answer"] == SAFE_UNKNOWN_ANSWER
    assert response.json()["citations"] == []


def test_env_helpers_read_llm_provider_settings(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_MAX_NEW_TOKENS", "120")
    monkeypatch.setenv("LLM_TEMPERATURE", "0.2")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-key")

    assert _env_int("LLM_MAX_NEW_TOKENS", 80) == 120
    assert _env_float("LLM_TEMPERATURE", 0.0) == 0.2
    assert _llm_api_keys()["GEMINI_API_KEY"] == "gemini-key"


def _service() -> FakeChatService:
    return FakeChatService(
        ChatAnswer(
            answer="Réponse sourcée [1].",
            citations=[
                Citation(
                    source_id="meteo-des-forets-realtime",
                    title="Meteo des forets 33",
                    document_url="https://example.com/doc",
                    canonical_url="https://example.com/canonical",
                    score=0.91,
                    published_at="2026-07-28T14:50:04+00:00",
                    collected_at="2026-07-29T13:54:08+00:00",
                )
            ],
            retrieved_count=1,
            model_name="fake-llm",
        )
    )
