from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, cast

from chatbot_incendie.embeddings import EmbeddedChunk

DEFAULT_MILVUS_URI = "http://localhost:19530"
DEFAULT_MILVUS_COLLECTION = "incendies_gironde_landes_2026"
DEFAULT_VECTOR_DIMENSION = 384
VECTOR_FIELD = "vector"
CHUNK_ID_FIELD = "chunk_id"
METADATA_FIELDS = [
    "source_id",
    "document_url",
    "canonical_url",
    "title",
    "content",
    "chunk_index",
    "chunk_count",
    "published_at",
    "collected_at",
]


class MilvusClientProtocol(Protocol):
    def has_collection(self, collection_name: str) -> bool: ...

    def load_collection(self, collection_name: str) -> object: ...

    def flush(self, collection_name: str) -> object: ...

    def create_collection(
        self,
        *,
        collection_name: str,
        schema: object,
        index_params: object,
    ) -> object: ...

    def upsert(self, collection_name: str, data: list[dict[str, object]]) -> dict[str, object]: ...

    def search(
        self,
        *,
        collection_name: str,
        data: list[list[float]],
        limit: int,
        output_fields: list[str],
        anns_field: str,
        search_params: dict[str, object],
    ) -> list[list[dict[str, object]]]: ...


@dataclass(frozen=True)
class MilvusConfig:
    uri: str = DEFAULT_MILVUS_URI
    collection_name: str = DEFAULT_MILVUS_COLLECTION
    vector_dimension: int = DEFAULT_VECTOR_DIMENSION

    def __post_init__(self) -> None:
        if not self.uri.strip():
            raise ValueError("Milvus URI must not be empty")
        if not self.collection_name.strip():
            raise ValueError("Milvus collection name must not be empty")
        if self.vector_dimension <= 0:
            raise ValueError("Milvus vector dimension must be greater than 0")


@dataclass(frozen=True)
class MilvusSearchResult:
    chunk_id: str
    score: float
    source_id: str
    document_url: str
    canonical_url: str | None
    title: str | None
    content: str
    chunk_index: int
    chunk_count: int
    published_at: str | None
    collected_at: str | None


def ensure_collection(
    config: MilvusConfig,
    client: MilvusClientProtocol | None = None,
) -> bool:
    milvus = client or _create_milvus_client(config)
    if milvus.has_collection(config.collection_name):
        milvus.load_collection(config.collection_name)
        return False

    schema, index_params = _build_collection_schema(config.vector_dimension)
    milvus.create_collection(
        collection_name=config.collection_name,
        schema=schema,
        index_params=index_params,
    )
    milvus.load_collection(config.collection_name)
    return True


def upsert_embedded_chunks(
    config: MilvusConfig,
    chunks: Sequence[EmbeddedChunk],
    client: MilvusClientProtocol | None = None,
) -> int:
    if not chunks:
        return 0

    records = [_record_from_chunk(config, chunk) for chunk in chunks]
    milvus = client or _create_milvus_client(config)
    result = milvus.upsert(collection_name=config.collection_name, data=records)
    milvus.flush(collection_name=config.collection_name)
    return _object_to_int(result.get("upsert_count", result.get("insert_count")), len(records))


def search_vectors(
    config: MilvusConfig,
    vectors: Sequence[Sequence[float]],
    limit: int = 5,
    client: MilvusClientProtocol | None = None,
) -> list[MilvusSearchResult]:
    if limit <= 0:
        raise ValueError("search limit must be greater than 0")
    if not vectors:
        return []

    query_vectors = [_validated_vector(config, vector) for vector in vectors]
    milvus = client or _create_milvus_client(config)
    results = milvus.search(
        collection_name=config.collection_name,
        data=query_vectors,
        limit=limit,
        output_fields=[CHUNK_ID_FIELD, *METADATA_FIELDS],
        anns_field=VECTOR_FIELD,
        search_params={"metric_type": "COSINE"},
    )
    return [_search_result_from_hit(hit) for hits in results for hit in hits]


def chunk_id(chunk: EmbeddedChunk) -> str:
    stable_key = "|".join(
        [
            chunk.source_id,
            chunk.canonical_url or chunk.document_url,
            str(chunk.chunk_index),
        ]
    )
    return hashlib.sha256(stable_key.encode("utf-8")).hexdigest()


def _record_from_chunk(config: MilvusConfig, chunk: EmbeddedChunk) -> dict[str, object]:
    return {
        CHUNK_ID_FIELD: chunk_id(chunk),
        VECTOR_FIELD: _validated_vector(config, chunk.vector),
        "source_id": chunk.source_id,
        "document_url": chunk.document_url,
        "canonical_url": chunk.canonical_url or "",
        "title": chunk.title or "",
        "content": chunk.content,
        "chunk_index": chunk.chunk_index,
        "chunk_count": chunk.chunk_count,
        "published_at": _datetime_to_text(chunk.published_at),
        "collected_at": _datetime_to_text(chunk.collected_at),
    }


def _validated_vector(config: MilvusConfig, vector: Sequence[float]) -> list[float]:
    if len(vector) != config.vector_dimension:
        raise ValueError(
            "Milvus vector dimension mismatch: "
            f"expected {config.vector_dimension}, got {len(vector)}"
        )
    return [float(value) for value in vector]


def _search_result_from_hit(hit: dict[str, object]) -> MilvusSearchResult:
    entity = cast(dict[str, object], hit.get("entity", {}))
    chunk_id_value = _field_as_text(entity, CHUNK_ID_FIELD) or _field_as_text(hit, "id")
    if chunk_id_value is None:
        raise ValueError("Milvus search hit is missing chunk id")
    return MilvusSearchResult(
        chunk_id=chunk_id_value,
        score=_object_to_float(hit.get("distance", hit.get("score")), 0.0),
        source_id=_required_text(entity, "source_id"),
        document_url=_required_text(entity, "document_url"),
        canonical_url=_empty_to_none(_field_as_text(entity, "canonical_url")),
        title=_empty_to_none(_field_as_text(entity, "title")),
        content=_required_text(entity, "content"),
        chunk_index=_required_int(entity, "chunk_index"),
        chunk_count=_required_int(entity, "chunk_count"),
        published_at=_empty_to_none(_field_as_text(entity, "published_at")),
        collected_at=_empty_to_none(_field_as_text(entity, "collected_at")),
    )


def _build_collection_schema(vector_dimension: int) -> tuple[object, object]:
    from pymilvus import DataType, MilvusClient  # type: ignore[import-untyped]

    schema = MilvusClient.create_schema(auto_id=False, enable_dynamic_field=False)
    schema.add_field(
        field_name=CHUNK_ID_FIELD,
        datatype=DataType.VARCHAR,
        is_primary=True,
        max_length=128,
    )
    schema.add_field(field_name=VECTOR_FIELD, datatype=DataType.FLOAT_VECTOR, dim=vector_dimension)
    schema.add_field(field_name="source_id", datatype=DataType.VARCHAR, max_length=128)
    schema.add_field(field_name="document_url", datatype=DataType.VARCHAR, max_length=2048)
    schema.add_field(field_name="canonical_url", datatype=DataType.VARCHAR, max_length=2048)
    schema.add_field(field_name="title", datatype=DataType.VARCHAR, max_length=1024)
    schema.add_field(field_name="content", datatype=DataType.VARCHAR, max_length=8192)
    schema.add_field(field_name="chunk_index", datatype=DataType.INT64)
    schema.add_field(field_name="chunk_count", datatype=DataType.INT64)
    schema.add_field(field_name="published_at", datatype=DataType.VARCHAR, max_length=64)
    schema.add_field(field_name="collected_at", datatype=DataType.VARCHAR, max_length=64)

    index_params = MilvusClient.prepare_index_params()
    index_params.add_index(
        field_name=VECTOR_FIELD,
        index_type="AUTOINDEX",
        metric_type="COSINE",
    )
    return schema, index_params


def _create_milvus_client(config: MilvusConfig) -> MilvusClientProtocol:
    from pymilvus import MilvusClient

    return cast(MilvusClientProtocol, MilvusClient(uri=config.uri))


def _datetime_to_text(value: datetime | None) -> str:
    return value.isoformat() if value is not None else ""


def _field_as_text(data: dict[str, object], field: str) -> str | None:
    value = data.get(field)
    return value if isinstance(value, str) else None


def _required_text(data: dict[str, object], field: str) -> str:
    value = _field_as_text(data, field)
    if value is None:
        raise ValueError(f"Milvus search hit field must be a string: {field}")
    return value


def _required_int(data: dict[str, object], field: str) -> int:
    value = data.get(field)
    if isinstance(value, int):
        return value
    raise ValueError(f"Milvus search hit field must be an int: {field}")


def _object_to_int(value: object, default: int) -> int:
    if isinstance(value, int):
        return value
    return default


def _object_to_float(value: object, default: float) -> float:
    if isinstance(value, int | float):
        return float(value)
    return default


def _empty_to_none(value: str | None) -> str | None:
    return value or None
