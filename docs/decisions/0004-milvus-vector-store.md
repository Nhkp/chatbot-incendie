# 0004 - Milvus vector store

## Decision

The project uses local Milvus as the first vector store for embedded chunks. Milvus is
started manually with Docker Compose and accessed through a thin `pymilvus` client
wrapper.

## Context

The ingestion, cleaning, chunking, and embedding contracts are already implemented.
The next RAG layer needs a searchable vector index, but retrieval scoring, answer
generation, Streamlit, and Airflow are separate milestones.

## Consequences

- Unit tests use fake Milvus clients and do not require Docker.
- Manual smoke tests can index Météo-France JSONL data into local Milvus.
- Embedded chunk metadata is stored with each vector so later retrieval can assemble
  citations.
- Parquet remains a future curated-data optimization, not part of this milestone.
