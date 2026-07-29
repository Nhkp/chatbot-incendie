from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from chatbot_incendie.chunking import Chunk


class EmbeddingModel(Protocol):
    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]: ...


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
