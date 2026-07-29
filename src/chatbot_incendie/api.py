from __future__ import annotations

import os
from functools import lru_cache
from typing import Protocol

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from chatbot_incendie.llm import DEFAULT_LLM_MODEL
from chatbot_incendie.milvus_store import DEFAULT_MILVUS_COLLECTION, DEFAULT_MILVUS_URI
from chatbot_incendie.rag import ChatAnswer, ResponseMode, build_default_rag_service

DEFAULT_LLM_MAX_NEW_TOKENS = 80


class ChatService(Protocol):
    def answer_question(self, question: str, top_k: int = 5) -> ChatAnswer: ...


class ChatRequest(BaseModel):
    question: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=10)


class CitationResponse(BaseModel):
    source_id: str
    title: str | None
    document_url: str
    canonical_url: str | None
    score: float
    published_at: str | None
    collected_at: str | None


class ChatResponse(BaseModel):
    answer: str
    citations: list[CitationResponse]
    retrieved_count: int
    model_name: str


def create_app(service: ChatService | None = None) -> FastAPI:
    app = FastAPI(title="chatbot-incendie API")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/chat")
    def chat(request: ChatRequest) -> ChatResponse:
        if not request.question.strip():
            raise HTTPException(status_code=422, detail="question must not be empty")
        chat_service = service or _default_service()
        try:
            answer = chat_service.answer_question(request.question, request.top_k)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return ChatResponse(
            answer=answer.answer,
            citations=[
                CitationResponse(
                    source_id=citation.source_id,
                    title=citation.title,
                    document_url=citation.document_url,
                    canonical_url=citation.canonical_url,
                    score=citation.score,
                    published_at=citation.published_at,
                    collected_at=citation.collected_at,
                )
                for citation in answer.citations
            ],
            retrieved_count=answer.retrieved_count,
            model_name=answer.model_name,
        )

    return app


@lru_cache(maxsize=1)
def _default_service() -> ChatService:
    return build_default_rag_service(
        milvus_uri=os.environ.get("MILVUS_URI", DEFAULT_MILVUS_URI),
        collection_name=os.environ.get("MILVUS_COLLECTION", DEFAULT_MILVUS_COLLECTION),
        llm_model_name=os.environ.get("LLM_MODEL_NAME", DEFAULT_LLM_MODEL),
        llm_max_new_tokens=_env_int("LLM_MAX_NEW_TOKENS", DEFAULT_LLM_MAX_NEW_TOKENS),
        response_mode=ResponseMode(os.environ.get("RAG_RESPONSE_MODE", ResponseMode.EXTRACTIVE)),
    )


app = create_app()


def _env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None:
        return default
    return int(value)
