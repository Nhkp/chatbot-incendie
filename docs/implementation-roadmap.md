# Implementation roadmap

## First application commit

Build only the domain/data models and the source registry.

- Add typed data objects for sources and raw documents.
- Add a source registry loaded from a YAML or TOML file under `config/`.
- Validate source id, name, type, URL, status, usage notes, and rate-limit notes.
- Add unit tests for model validation and registry loading.
- Do not add Airflow, Milvus, Streamlit, scraping, or LLM dependencies yet.

## Milestones

1. Domain models and source registry. Done.
2. Ingestion skeleton that writes local JSONL raw documents. Done.
3. Source connectors for approved API-first sources. First connector done.
4. Cleaning, deduplication, and metadata normalization. Done for v1.
5. Chunking strategy and deterministic chunk tests. First deterministic chunker done.
6. Embedding interface and local embedding model selection. Done.
7. Milvus storage and retrieval client. Done for v1.
8. Retrieval scoring and citation assembly. Minimal Milvus citations done.
9. Small open LLM interface and prompt contract. Minimal local generator done.
10. Streamlit interface with answer, citations, and freshness metadata. Minimal chat UI done.
11. Airflow DAG that orchestrates the already-tested ingestion pipeline hourly.

## Implementation rules

- Keep each milestone small enough for independent commits.
- Keep Airflow thin: orchestration only, no business logic in DAG files.
- Keep tests offline and deterministic unless a test is explicitly marked integration.
- Prefer fake clients in unit tests before adding real service dependencies.
- Update `docs/decisions/` when selecting the embedding model, LLM, or storage schema.
