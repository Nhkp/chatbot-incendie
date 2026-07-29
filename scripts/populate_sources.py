from __future__ import annotations

import argparse
import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from chatbot_incendie.chunking import DEFAULT_MAX_CHARS, DEFAULT_OVERLAP_CHARS, chunk_documents
from chatbot_incendie.connectors import (
    GEORISQUES_API_BASE_URL,
    METEO_DES_FORETS_API_BASE_URL,
    METEO_FRANCE_VIGILANCE_API_BASE_URL,
    GeorisquesConnector,
    MeteoDesForetsRealtimeConnector,
    MeteoFranceVigilanceConnector,
    NasaFirmsAreaConnector,
    SourceConnector,
    UrlopenTextClient,
)
from chatbot_incendie.embeddings import (
    DEFAULT_EMBEDDING_MODEL,
    SentenceTransformerEmbeddingModel,
    embed_chunks,
)
from chatbot_incendie.jsonl_store import read_raw_documents
from chatbot_incendie.milvus_store import (
    DEFAULT_MILVUS_COLLECTION,
    DEFAULT_MILVUS_URI,
    DEFAULT_VECTOR_DIMENSION,
    MilvusConfig,
    ensure_collection,
    upsert_embedded_chunks,
)
from chatbot_incendie.pipeline import run_clean_ingestion_pipeline
from chatbot_incendie.source_registry import get_source_by_id, load_sources

SOURCE_IDS = (
    "meteo-des-forets-realtime",
    "nasa-firms-area-api",
    "meteo-france-vigilance-api",
    "georisques-api",
)


@dataclass(frozen=True)
class ConnectorSpec:
    source_id: str
    build: Callable[[UrlopenTextClient], SourceConnector]
    required_env_var: str | None = None


def main() -> int:
    args = _parse_args()
    _load_dotenv(args.env_file)

    sources = load_sources(args.sources)
    client = UrlopenTextClient(timeout_seconds=args.timeout_seconds)
    config = MilvusConfig(
        uri=args.uri,
        collection_name=args.collection,
        vector_dimension=args.vector_dimension,
    )
    model: SentenceTransformerEmbeddingModel | None = None
    collected_at = datetime.now(UTC)
    successes = 0

    for spec in _connector_specs():
        source = get_source_by_id(sources, spec.source_id)
        if source is None:
            print(f"{spec.source_id}: skipped, missing from {args.sources}")
            continue
        if spec.required_env_var and not os.environ.get(spec.required_env_var, "").strip():
            print(f"{spec.source_id}: skipped, missing {spec.required_env_var}")
            continue

        try:
            pipeline_result = run_clean_ingestion_pipeline(
                source=source,
                connector=spec.build(client),
                output_dir=args.output_dir,
                collected_at=collected_at,
            )
            documents = read_raw_documents(pipeline_result.output_path)
            chunks = chunk_documents(
                documents,
                max_chars=args.max_chars,
                overlap_chars=args.overlap_chars,
            )
            if chunks and model is None:
                model = SentenceTransformerEmbeddingModel(model_name=args.model)
                ensure_collection(config)
            embedded_chunks = embed_chunks(chunks, model) if model is not None else []
            upserted = upsert_embedded_chunks(config, embedded_chunks) if embedded_chunks else 0
        except Exception as error:  # noqa: BLE001
            print(f"{spec.source_id}: failed: {error}")
            continue

        successes += 1
        print(
            f"{spec.source_id}: raw={pipeline_result.input_count} "
            f"cleaned={pipeline_result.output_count} "
            f"duplicates={pipeline_result.duplicate_count} "
            f"rejected={pipeline_result.rejected_count} "
            f"chunks={len(chunks)} upserted={upserted} "
            f"path={pipeline_result.output_path}"
        )

    return 0 if successes else 1


def _connector_specs() -> list[ConnectorSpec]:
    return [
        ConnectorSpec(
            source_id="meteo-des-forets-realtime",
            required_env_var="METEO_FRANCE_API_KEY",
            build=lambda client: MeteoDesForetsRealtimeConnector(
                client=client,
                api_key=os.environ.get("METEO_FRANCE_API_KEY", ""),
                base_url=os.environ.get("METEO_FRANCE_API_BASE_URL", METEO_DES_FORETS_API_BASE_URL),
            ),
        ),
        ConnectorSpec(
            source_id="nasa-firms-area-api",
            required_env_var="NASA_FIRMS_MAP_KEY",
            build=lambda client: NasaFirmsAreaConnector(
                client=client,
                map_key=os.environ.get("NASA_FIRMS_MAP_KEY", ""),
            ),
        ),
        ConnectorSpec(
            source_id="meteo-france-vigilance-api",
            required_env_var="METEO_FRANCE_API_KEY",
            build=lambda client: MeteoFranceVigilanceConnector(
                client=client,
                api_key=os.environ.get("METEO_FRANCE_API_KEY", ""),
                base_url=os.environ.get(
                    "METEO_FRANCE_VIGILANCE_API_BASE_URL",
                    METEO_FRANCE_VIGILANCE_API_BASE_URL,
                ),
            ),
        ),
        ConnectorSpec(
            source_id="georisques-api",
            build=lambda client: GeorisquesConnector(
                client=client,
                base_url=os.environ.get("GEORISQUES_API_BASE_URL", GEORISQUES_API_BASE_URL),
            ),
        ),
    ]


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        key = key.strip().removeprefix("export ").strip()
        if key and key not in os.environ:
            os.environ[key] = value.strip().strip("\"'")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch implemented open-data sources and index them in Milvus."
    )
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument("--sources", type=Path, default=Path("config/sources.toml"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--uri", default=os.environ.get("MILVUS_URI", DEFAULT_MILVUS_URI))
    parser.add_argument(
        "--collection",
        default=os.environ.get("MILVUS_COLLECTION", DEFAULT_MILVUS_COLLECTION),
    )
    parser.add_argument("--vector-dimension", type=int, default=DEFAULT_VECTOR_DIMENSION)
    parser.add_argument(
        "--model",
        default=os.environ.get("EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL),
    )
    parser.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS)
    parser.add_argument("--overlap-chars", type=int, default=DEFAULT_OVERLAP_CHARS)
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
