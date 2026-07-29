from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol, cast

from chatbot_incendie.chunking import Chunk

DEFAULT_EMBEDDING_MODEL = "intfloat/multilingual-e5-small"


class EmbeddingModel(Protocol):
    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]: ...


class _SentenceTransformerBackend(Protocol):
    def encode_document(
        self,
        sentences: Sequence[str],
        *,
        normalize_embeddings: bool,
    ) -> Any: ...


class _VectorArray(Protocol):
    def tolist(self) -> list[list[float]]: ...


@dataclass(frozen=True)
class EmbeddedChunk:
    source_id: str
    document_url: str
    canonical_url: str | None
    title: str | None
    content: str
    chunk_index: int
    chunk_count: int
    published_at: datetime | None
    collected_at: datetime | None
    vector: list[float]


@dataclass(frozen=True)
class SentenceTransformerEmbeddingModel:
    model_name: str = DEFAULT_EMBEDDING_MODEL
    normalize_embeddings: bool = True
    backend: _SentenceTransformerBackend | None = None

    def __post_init__(self) -> None:
        if self.backend is None:
            object.__setattr__(self, "backend", _load_sentence_transformer(self.model_name))

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        backend = self.backend
        if backend is None:
            raise ValueError("sentence-transformers backend is not initialized")
        encoded = backend.encode_document(
            list(texts),
            normalize_embeddings=self.normalize_embeddings,
        )
        return _vectors_to_lists(encoded)


def embed_chunks(chunks: Sequence[Chunk], model: EmbeddingModel) -> list[EmbeddedChunk]:
    if not chunks:
        return []

    vectors = model.embed_texts([chunk.content for chunk in chunks])
    if len(vectors) != len(chunks):
        raise ValueError("embedding model must return one vector per chunk")

    vector_size = _validate_vector(vectors[0])
    embedded_chunks: list[EmbeddedChunk] = []
    for chunk, vector in zip(chunks, vectors, strict=True):
        if _validate_vector(vector) != vector_size:
            raise ValueError("embedding vectors must have a stable dimension")
        embedded_chunks.append(
            EmbeddedChunk(
                source_id=chunk.source_id,
                document_url=chunk.document_url,
                canonical_url=chunk.canonical_url,
                title=chunk.title,
                content=chunk.content,
                chunk_index=chunk.chunk_index,
                chunk_count=chunk.chunk_count,
                published_at=chunk.published_at,
                collected_at=chunk.collected_at,
                vector=vector,
            )
        )
    return embedded_chunks


def _validate_vector(vector: Sequence[float]) -> int:
    if not vector:
        raise ValueError("embedding vector must not be empty")
    return len(vector)


def _load_sentence_transformer(model_name: str) -> _SentenceTransformerBackend:
    from sentence_transformers import SentenceTransformer

    return cast(_SentenceTransformerBackend, SentenceTransformer(model_name))


def _vectors_to_lists(vectors: object) -> list[list[float]]:
    if hasattr(vectors, "tolist"):
        vectors = cast(_VectorArray, vectors).tolist()
    return [[float(value) for value in vector] for vector in cast(list[list[float]], vectors)]
