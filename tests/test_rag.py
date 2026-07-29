from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from chatbot_incendie.llm import TextGenerator
from chatbot_incendie.milvus_store import MilvusConfig, MilvusSearchResult
from chatbot_incendie.rag import (
    SAFE_UNKNOWN_ANSWER,
    ExtractiveGenerator,
    RagService,
    ResponseMode,
    build_default_rag_service,
    build_prompt,
)


@dataclass(frozen=True)
class FakeEmbedder:
    vector: list[float]

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        return [self.vector for _ in texts]


@dataclass
class FakeGenerator(TextGenerator):
    model_name: str = "fake-llm"
    prompts: list[str] | None = None

    def generate(self, prompt: str) -> str:
        if self.prompts is not None:
            self.prompts.append(prompt)
        return "Le risque feu de forêt en Gironde est élevé selon la source [1]."


def test_rag_service_returns_answer_and_citations() -> None:
    prompts: list[str] = []
    service = RagService(
        embedder=FakeEmbedder([0.1, 0.2]),
        generator=FakeGenerator(prompts=prompts),
        milvus_config=MilvusConfig(vector_dimension=2),
        search=_fake_search,
    )

    answer = service.answer_question("Quel est le risque en Gironde ?", top_k=1)

    assert answer.answer.startswith("Le risque feu de forêt")
    assert answer.retrieved_count == 1
    assert answer.model_name == "fake-llm"
    assert answer.citations[0].source_id == "meteo-des-forets-realtime"
    assert "Quel est le risque en Gironde ?" in prompts[0]


def test_rag_service_can_return_extractive_answer_without_llm_prompt() -> None:
    prompts: list[str] = []
    service = RagService(
        embedder=FakeEmbedder([0.1, 0.2]),
        generator=ExtractiveGenerator(),
        milvus_config=MilvusConfig(vector_dimension=2),
        search=_fake_search,
    )

    answer = service.answer_question("Quel est le risque en Gironde ?", top_k=1)

    assert "Danger feu de foret J+1: niveau 3" in answer.answer
    assert "ne remplacent pas les consignes" in answer.answer
    assert answer.model_name == "extractive"
    assert prompts == []


def test_rag_service_returns_safe_unknown_without_context() -> None:
    service = RagService(
        embedder=FakeEmbedder([0.1, 0.2]),
        generator=FakeGenerator(prompts=[]),
        milvus_config=MilvusConfig(vector_dimension=2),
        search=lambda config, vectors, limit: [],
    )

    answer = service.answer_question("Puis-je rentrer chez moi ?", top_k=5)

    assert answer.answer == SAFE_UNKNOWN_ANSWER
    assert answer.citations == []
    assert answer.retrieved_count == 0


def test_build_prompt_constrains_answer_to_context_and_safety() -> None:
    prompt = build_prompt("J'habite à Audenge, puis-je rentrer chez moi ?", [_result()])

    assert "Réponds en français" in prompt
    assert "uniquement avec le contexte fourni" in prompt
    assert "Ne remplace jamais les consignes" in prompt
    assert "services officiels" in prompt
    assert "J'habite à Audenge" in prompt


def test_build_default_rag_service_uses_extractive_mode_without_llm() -> None:
    service = build_default_rag_service(response_mode=ResponseMode.EXTRACTIVE)

    assert isinstance(service.generator, ExtractiveGenerator)


def _fake_search(
    config: MilvusConfig,
    vectors: list[list[float]],
    limit: int,
) -> list[MilvusSearchResult]:
    assert config.vector_dimension == 2
    assert vectors == [[0.1, 0.2]]
    assert limit == 1
    return [_result()]


def _result() -> MilvusSearchResult:
    return MilvusSearchResult(
        chunk_id="chunk-a",
        score=0.91,
        source_id="meteo-des-forets-realtime",
        document_url="https://example.com/doc",
        canonical_url="https://example.com/canonical",
        title="Meteo des forets 33",
        content="Danger feu de foret J+1: niveau 3 (eleve).",
        chunk_index=0,
        chunk_count=1,
        published_at="2026-07-28T14:50:04+00:00",
        collected_at="2026-07-29T13:54:08+00:00",
    )
