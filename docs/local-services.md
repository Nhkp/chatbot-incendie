# Local services

This project will need local services later, but they are intentionally not added yet.

## Planned services

- Milvus for vector search.
- Airflow for hourly ingestion orchestration.
- Optional object storage for raw documents and artifacts.
- Streamlit for the v1 web interface.

## Rule

Add Docker Compose only when the first concrete service is implemented. Until then,
keep the workspace lightweight and avoid unused containers.
