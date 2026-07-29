from __future__ import annotations

import argparse
from pathlib import Path

from chatbot_incendie.chunking import chunk_documents
from chatbot_incendie.cleaning import clean_and_deduplicate
from chatbot_incendie.embeddings import (
    DEFAULT_EMBEDDING_MODEL,
    SentenceTransformerEmbeddingModel,
    embed_chunks,
)
from chatbot_incendie.jsonl_store import read_raw_documents


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
    vector_dimension = len(embedded_chunks[0].vector) if embedded_chunks else 0

    print(f"Read {len(documents)} raw documents from {args.input}")
    print(
        "Kept "
        f"{cleaned.output_count} cleaned documents "
        f"({cleaned.duplicate_count} duplicates, {cleaned.rejected_count} rejected)"
    )
    print(f"Embedded {len(embedded_chunks)} chunks with vector dimension {vector_dimension}")
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a local embedding smoke test.")
    parser.add_argument("input", type=Path, help="Path to a raw JSONL file.")
    parser.add_argument("--model", default=DEFAULT_EMBEDDING_MODEL)
    parser.add_argument("--max-chars", type=int, default=800)
    parser.add_argument("--overlap-chars", type=int, default=120)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
