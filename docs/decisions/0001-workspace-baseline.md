# 0001 - Workspace baseline

## Decision

The project uses Python 3.11, `uv`, `ruff`, `mypy`, `pytest`, `pytest-cov`, and
`pre-commit`.

## Context

Airflow and RAG/ML dependencies are more stable on Python 3.11 than on Python 3.14.
The repository is still empty: this is the right time to set conventions before adding
Streamlit, Milvus, and Airflow.

## Consequences

- Local and CI checks use the same commands.
- Minimum coverage is set to 80%.
- Heavy application choices remain outside this decision.
