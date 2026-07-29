from __future__ import annotations

import argparse
import os
from pathlib import Path

from chatbot_incendie.chunking import chunk_documents
from chatbot_incendie.cleaning import clean_and_deduplicate
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
    search_vectors,
    upsert_embedded_chunks,
)


def main() -> int:
    args = _parse_args()
    documents = read_raw_documents(args.input)
    cleaned = clean_and_deduplicate(documents)
    chunks = chunk_documents(
        cleaned.documents,
        max_chars=args.max_chars,
        overlap_chars=args.overlap_chars,
    )
    embedded_chunks = embed_chunks(
        chunks,
        SentenceTransformerEmbeddingModel(model_name=args.model),
    )
    config = MilvusConfig(
        uri=args.uri,
        collection_name=args.collection,
        vector_dimension=args.vector_dimension,
    )

    created = ensure_collection(config)
    upsert_count = upsert_embedded_chunks(config, embedded_chunks)
    search_count = (
        len(search_vectors(config, [embedded_chunks[0].vector], limit=1)) if embedded_chunks else 0
    )

    print(f"Collection: {config.collection_name} ({'created' if created else 'existing'})")
    print(f"Embedded chunks: {len(embedded_chunks)}")
    print(f"Upserted chunks: {upsert_count}")
    print(f"Smoke search results: {search_count}")
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Index Météo des forêts JSONL data in Milvus.")
    parser.add_argument("input", type=Path, help="Path to a raw JSONL file.")
    parser.add_argument("--uri", default=os.environ.get("MILVUS_URI", DEFAULT_MILVUS_URI))
    parser.add_argument(
        "--collection",
        default=os.environ.get("MILVUS_COLLECTION", DEFAULT_MILVUS_COLLECTION),
    )
    parser.add_argument("--vector-dimension", type=int, default=DEFAULT_VECTOR_DIMENSION)
    parser.add_argument("--model", default=DEFAULT_EMBEDDING_MODEL)
    parser.add_argument("--max-chars", type=int, default=800)
    parser.add_argument("--overlap-chars", type=int, default=120)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
