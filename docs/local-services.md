# Local services

The project uses Docker Compose for local services that are needed by implemented
features.

## Milvus

Milvus is the local vector store for embedded chunks.

```bash
docker compose up -d
docker compose ps
```

The Milvus API is exposed at `http://localhost:19530`. Local service data is stored
under ignored `milvus/` and `minio/` directories.

If port `19530` is already allocated, another local Milvus instance is running. Either
reuse it with `MILVUS_URI=http://localhost:19530` or stop it before starting this
project's Compose stack.

Index generated Météo-France JSONL data with:

```bash
uv run python scripts/index_meteo_des_forets_milvus.py data/raw/2026-07-29/meteo-des-forets-realtime.jsonl
```

## Planned services

- Airflow for hourly ingestion orchestration.
- Streamlit for the v1 interface.
- Optional object storage for raw documents and artifacts.
