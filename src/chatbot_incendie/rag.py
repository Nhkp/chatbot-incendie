from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from chatbot_incendie.embeddings import EmbeddingModel, SentenceTransformerEmbeddingModel
from chatbot_incendie.llm import DEFAULT_LLM_MODEL, LocalTransformersGenerator, TextGenerator
from chatbot_incendie.milvus_store import (
    DEFAULT_MILVUS_COLLECTION,
    DEFAULT_MILVUS_URI,
    DEFAULT_VECTOR_DIMENSION,
    MilvusConfig,
    MilvusSearchResult,
    search_vectors,
)

SAFE_UNKNOWN_ANSWER = (
    "Je ne sais pas répondre avec les sources actuellement indexées. "
    "Consultez les sources officielles locales, la préfecture, la mairie ou les services "
    "de secours en cas de danger immédiat."
)


SearchFunction = Callable[[MilvusConfig, list[list[float]], int], list[MilvusSearchResult]]


@dataclass(frozen=True)
class Citation:
    source_id: str
    title: str | None
    document_url: str
    canonical_url: str | None
    score: float
    published_at: str | None
    collected_at: str | None


@dataclass(frozen=True)
class ChatAnswer:
    answer: str
    citations: list[Citation]
    retrieved_count: int
    model_name: str


@dataclass(frozen=True)
class RagService:
    embedder: EmbeddingModel
    generator: TextGenerator
    milvus_config: MilvusConfig
    search: SearchFunction = search_vectors

    def answer_question(self, question: str, top_k: int = 5) -> ChatAnswer:
        question = question.strip()
        if not question:
            raise ValueError("question must not be empty")
        if top_k <= 0:
            raise ValueError("top_k must be greater than 0")

        query_vectors = self.embedder.embed_texts([question])
        if len(query_vectors) != 1:
            raise ValueError("embedding model must return one vector for the question")

        results = self.search(self.milvus_config, query_vectors, top_k)
        citations = [_citation_from_result(result) for result in results]
        if not results:
            return ChatAnswer(
                answer=SAFE_UNKNOWN_ANSWER,
                citations=[],
                retrieved_count=0,
                model_name=self.generator.model_name,
            )

        prompt = build_prompt(question, results)
        answer = self.generator.generate(prompt).strip() or SAFE_UNKNOWN_ANSWER
        return ChatAnswer(
            answer=answer,
            citations=citations,
            retrieved_count=len(results),
            model_name=self.generator.model_name,
        )


def build_default_rag_service(
    *,
    milvus_uri: str = DEFAULT_MILVUS_URI,
    collection_name: str = DEFAULT_MILVUS_COLLECTION,
    llm_model_name: str = DEFAULT_LLM_MODEL,
) -> RagService:
    return RagService(
        embedder=SentenceTransformerEmbeddingModel(),
        generator=LocalTransformersGenerator(model_name=llm_model_name),
        milvus_config=MilvusConfig(
            uri=milvus_uri,
            collection_name=collection_name,
            vector_dimension=DEFAULT_VECTOR_DIMENSION,
        ),
    )


def build_prompt(question: str, results: list[MilvusSearchResult]) -> str:
    context = "\n\n".join(_context_line(index, result) for index, result in enumerate(results, 1))
    return (
        "Tu es un assistant RAG sur les incendies et le risque feu de forêt en Gironde "
        "et dans les Landes en 2026.\n"
        "Réponds en français, uniquement avec le contexte fourni.\n"
        "Cite les sources avec les numéros [1], [2], etc.\n"
        "Si le contexte ne suffit pas, dis clairement que tu ne sais pas.\n"
        "Ne remplace jamais les consignes de la mairie, de la préfecture ou des secours; "
        "en cas de danger immédiat, recommande de contacter les services officiels.\n\n"
        f"Question: {question}\n\n"
        f"Contexte:\n{context}\n\n"
        "Réponse:"
    )


def _context_line(index: int, result: MilvusSearchResult) -> str:
    title = result.title or result.source_id
    return (
        f"[{index}] {title}\n"
        f"Source: {result.source_id}\n"
        f"URL: {result.canonical_url or result.document_url}\n"
        f"Publié: {result.published_at or 'date inconnue'}\n"
        f"Collecté: {result.collected_at or 'date inconnue'}\n"
        f"Extrait: {result.content}"
    )


def _citation_from_result(result: MilvusSearchResult) -> Citation:
    return Citation(
        source_id=result.source_id,
        title=result.title,
        document_url=result.document_url,
        canonical_url=result.canonical_url,
        score=result.score,
        published_at=result.published_at,
        collected_at=result.collected_at,
    )
