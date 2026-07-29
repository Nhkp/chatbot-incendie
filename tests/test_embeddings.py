from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

import pytest

from chatbot_incendie.chunking import Chunk, chunk_documents
from chatbot_incendie.cleaning import clean_and_deduplicate
from chatbot_incendie.connectors import parse_meteo_des_forets_archive
from chatbot_incendie.domain import Source, SourceStatus, SourceType
from chatbot_incendie.embeddings import (
    DEFAULT_EMBEDDING_MODEL,
    SentenceTransformerEmbeddingModel,
    embed_chunks,
)


@dataclass(frozen=True)
class DeterministicEmbeddingModel:
    dimensions: int = 4

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        return [_vector_from_text(text, self.dimensions) for text in texts]


@dataclass(frozen=True)
class StaticEmbeddingModel:
    vectors: list[list[float]]

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        return self.vectors


@dataclass
class FakeSentenceTransformerBackend:
    vectors: list[list[float]]
    calls: list[tuple[list[str], bool]]

    def encode_document(
        self,
        sentences: Sequence[str],
        *,
        normalize_embeddings: bool,
    ) -> list[list[float]]:
        self.calls.append((list(sentences), normalize_embeddings))
        return self.vectors


def test_embed_chunks_embeds_one_chunk_with_metadata() -> None:
    chunk = _chunk("Meteo des forets Gironde")

    embedded = embed_chunks([chunk], DeterministicEmbeddingModel())

    assert len(embedded) == 1
    assert embedded[0].source_id == chunk.source_id
    assert embedded[0].document_url == chunk.document_url
    assert embedded[0].canonical_url == chunk.canonical_url
    assert embedded[0].title == chunk.title
    assert embedded[0].content == chunk.content
    assert embedded[0].chunk_index == chunk.chunk_index
    assert embedded[0].chunk_count == chunk.chunk_count
    assert embedded[0].published_at == chunk.published_at
    assert embedded[0].collected_at == chunk.collected_at
    assert len(embedded[0].vector) == 4


def test_embed_chunks_preserves_order_for_multiple_chunks() -> None:
    chunks = [_chunk("Alpha", index=0, count=2), _chunk("Beta", index=1, count=2)]

    embedded = embed_chunks(chunks, DeterministicEmbeddingModel())

    assert [chunk.content for chunk in embedded] == ["Alpha", "Beta"]
    assert embedded[0].vector != embedded[1].vector


def test_embed_chunks_handles_empty_input_without_calling_model() -> None:
    embedded = embed_chunks([], StaticEmbeddingModel([[1.0]]))

    assert embedded == []


def test_embed_chunks_rejects_empty_vectors() -> None:
    with pytest.raises(ValueError, match="vector must not be empty"):
        embed_chunks([_chunk("Alpha")], StaticEmbeddingModel([[]]))


def test_embed_chunks_rejects_inconsistent_vector_dimensions() -> None:
    chunks = [_chunk("Alpha", index=0, count=2), _chunk("Beta", index=1, count=2)]

    with pytest.raises(ValueError, match="stable dimension"):
        embed_chunks(chunks, StaticEmbeddingModel([[1.0, 2.0], [3.0]]))


def test_embed_chunks_rejects_wrong_vector_count() -> None:
    chunks = [_chunk("Alpha", index=0, count=2), _chunk("Beta", index=1, count=2)]

    with pytest.raises(ValueError, match="one vector per chunk"):
        embed_chunks(chunks, StaticEmbeddingModel([[1.0]]))


def test_meteo_des_forets_documents_flow_through_embeddings() -> None:
    documents = parse_meteo_des_forets_archive(
        csv_text=(
            "Reference_time,dep_code,niveau_j1,niveau_j2,nom_dep\n"
            "2026-07-29T17:00:00+00:00,33,3,4,Gironde\n"
            "2026-07-29T17:00:00+00:00,40,4,4,Landes\n"
        ),
        source=_source(),
        archive_url="https://example.com/mdf.csv",
    )
    cleaned = clean_and_deduplicate(documents)
    chunks = chunk_documents(cleaned.documents, max_chars=800, overlap_chars=120)

    embedded = embed_chunks(chunks, DeterministicEmbeddingModel())

    assert [chunk.source_id for chunk in embedded] == [
        "meteo-des-forets-archive",
        "meteo-des-forets-archive",
    ]
    assert [len(chunk.vector) for chunk in embedded] == [4, 4]


def test_sentence_transformer_embedding_model_uses_document_encoding() -> None:
    backend = FakeSentenceTransformerBackend(vectors=[[1, 2], [3, 4]], calls=[])
    model = SentenceTransformerEmbeddingModel(backend=backend)

    vectors = model.embed_texts(["passage a", "passage b"])

    assert vectors == [[1.0, 2.0], [3.0, 4.0]]
    assert backend.calls == [(["passage a", "passage b"], True)]
    assert model.model_name == DEFAULT_EMBEDDING_MODEL


def test_sentence_transformer_embedding_model_can_disable_normalization() -> None:
    backend = FakeSentenceTransformerBackend(vectors=[[1.0]], calls=[])
    model = SentenceTransformerEmbeddingModel(backend=backend, normalize_embeddings=False)

    assert model.embed_texts(["passage"]) == [[1.0]]
    assert backend.calls == [(["passage"], False)]


def _vector_from_text(text: str, dimensions: int) -> list[float]:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return [digest[index] / 255 for index in range(dimensions)]


def _chunk(content: str, *, index: int = 0, count: int = 1) -> Chunk:
    return Chunk(
        source_id="source-a",
        document_url="https://example.com/doc",
        canonical_url="https://example.com/canonical",
        title="Incident update",
        content=content,
        chunk_index=index,
        chunk_count=count,
        published_at=datetime(2026, 7, 29, 17, 0, tzinfo=UTC),
        collected_at=datetime(2026, 7, 29, 18, 0, tzinfo=UTC),
    )


def _source() -> Source:
    return Source(
        id="meteo-des-forets-archive",
        name="Meteo des forets archive",
        type=SourceType.OPEN_DATA,
        url="https://www.data.gouv.fr/datasets/archives-de-la-meteo-des-forets",
        status=SourceStatus.APPROVED,
        usage_notes="Open archive data for wildfire danger prevention context.",
        rate_limit_notes="Download archive files conservatively.",
    )
