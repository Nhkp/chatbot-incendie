from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

import pytest

from chatbot_incendie.embeddings import EmbeddedChunk
from chatbot_incendie.milvus_store import (
    DEFAULT_MILVUS_COLLECTION,
    DEFAULT_MILVUS_URI,
    DEFAULT_VECTOR_DIMENSION,
    MilvusConfig,
    chunk_id,
    ensure_collection,
    search_vectors,
    upsert_embedded_chunks,
)


@dataclass
class FakeMilvusClient:
    has_existing_collection: bool = False
    created_collections: list[dict[str, object]] = field(default_factory=list)
    upserted_records: list[dict[str, object]] = field(default_factory=list)
    search_calls: list[dict[str, object]] = field(default_factory=list)
    loaded_collections: list[str] = field(default_factory=list)
    flushed_collections: list[str] = field(default_factory=list)

    def has_collection(self, collection_name: str) -> bool:
        return self.has_existing_collection

    def load_collection(self, collection_name: str) -> object:
        self.loaded_collections.append(collection_name)
        return None

    def flush(self, collection_name: str) -> object:
        self.flushed_collections.append(collection_name)
        return None

    def create_collection(
        self,
        *,
        collection_name: str,
        schema: object,
        index_params: object,
    ) -> object:
        self.created_collections.append(
            {
                "collection_name": collection_name,
                "schema": schema,
                "index_params": index_params,
            }
        )
        return None

    def upsert(self, collection_name: str, data: list[dict[str, object]]) -> dict[str, object]:
        self.upserted_records.extend(data)
        return {"upsert_count": len(data)}

    def search(
        self,
        *,
        collection_name: str,
        data: list[list[float]],
        limit: int,
        output_fields: list[str],
        anns_field: str,
        search_params: dict[str, object],
    ) -> list[list[dict[str, object]]]:
        self.search_calls.append(
            {
                "collection_name": collection_name,
                "data": data,
                "limit": limit,
                "output_fields": output_fields,
                "anns_field": anns_field,
                "search_params": search_params,
            }
        )
        return [
            [
                {
                    "distance": 0.98,
                    "entity": {
                        "chunk_id": "chunk-a",
                        "source_id": "source-a",
                        "document_url": "https://example.com/doc",
                        "canonical_url": "https://example.com/canonical",
                        "title": "Incident update",
                        "content": "Meteo des forets Gironde",
                        "chunk_index": 0,
                        "chunk_count": 1,
                        "published_at": "2026-07-29T17:00:00+00:00",
                        "collected_at": "2026-07-29T18:00:00+00:00",
                    },
                }
            ]
        ]


def test_milvus_config_defaults() -> None:
    config = MilvusConfig()

    assert config.uri == DEFAULT_MILVUS_URI
    assert config.collection_name == DEFAULT_MILVUS_COLLECTION
    assert config.vector_dimension == DEFAULT_VECTOR_DIMENSION


def test_ensure_collection_creates_missing_collection() -> None:
    client = FakeMilvusClient()

    created = ensure_collection(MilvusConfig(), client=client)

    assert created is True
    assert client.created_collections[0]["collection_name"] == DEFAULT_MILVUS_COLLECTION
    assert client.loaded_collections == [DEFAULT_MILVUS_COLLECTION]


def test_ensure_collection_skips_existing_collection() -> None:
    client = FakeMilvusClient(has_existing_collection=True)

    created = ensure_collection(MilvusConfig(), client=client)

    assert created is False
    assert client.created_collections == []
    assert client.loaded_collections == [DEFAULT_MILVUS_COLLECTION]


def test_chunk_id_is_deterministic() -> None:
    chunk = _embedded_chunk()

    assert chunk_id(chunk) == chunk_id(chunk)


def test_upsert_embedded_chunks_writes_vectors_and_metadata() -> None:
    client = FakeMilvusClient()
    chunk = _embedded_chunk()

    count = upsert_embedded_chunks(MilvusConfig(vector_dimension=2), [chunk], client=client)

    assert count == 1
    assert client.flushed_collections == [DEFAULT_MILVUS_COLLECTION]
    assert client.upserted_records == [
        {
            "chunk_id": chunk_id(chunk),
            "vector": [0.1, 0.2],
            "source_id": "source-a",
            "document_url": "https://example.com/doc",
            "canonical_url": "https://example.com/canonical",
            "title": "Incident update",
            "content": "Meteo des forets Gironde",
            "chunk_index": 0,
            "chunk_count": 1,
            "published_at": "2026-07-29T17:00:00+00:00",
            "collected_at": "2026-07-29T18:00:00+00:00",
        }
    ]


def test_upsert_embedded_chunks_returns_zero_for_empty_input() -> None:
    client = FakeMilvusClient()

    count = upsert_embedded_chunks(MilvusConfig(), [], client=client)

    assert count == 0
    assert client.upserted_records == []


def test_upsert_embedded_chunks_rejects_wrong_vector_dimension() -> None:
    with pytest.raises(ValueError, match="dimension mismatch"):
        upsert_embedded_chunks(MilvusConfig(vector_dimension=384), [_embedded_chunk()])


def test_search_vectors_returns_flat_search_results() -> None:
    client = FakeMilvusClient()

    results = search_vectors(MilvusConfig(vector_dimension=2), [[0.1, 0.2]], client=client)

    assert len(results) == 1
    assert results[0].chunk_id == "chunk-a"
    assert results[0].score == 0.98
    assert results[0].content == "Meteo des forets Gironde"
    assert client.search_calls[0]["anns_field"] == "vector"
    assert client.search_calls[0]["search_params"] == {"metric_type": "COSINE"}


def test_search_vectors_rejects_invalid_limit() -> None:
    with pytest.raises(ValueError, match="limit"):
        search_vectors(MilvusConfig(), [[0.1]], limit=0)


def _embedded_chunk() -> EmbeddedChunk:
    return EmbeddedChunk(
        source_id="source-a",
        document_url="https://example.com/doc",
        canonical_url="https://example.com/canonical",
        title="Incident update",
        content="Meteo des forets Gironde",
        chunk_index=0,
        chunk_count=1,
        published_at=datetime(2026, 7, 29, 17, 0, tzinfo=UTC),
        collected_at=datetime(2026, 7, 29, 18, 0, tzinfo=UTC),
        vector=[0.1, 0.2],
    )
