# Target architecture

## Overview

The system will separate ingestion, indexing, and the user interface.

```text
Free sources + web news
        |
        v
Hourly Airflow DAG
        |
        v
Cleaning, deduplication, source metadata
        |
        v
Chunking + embeddings
        |
        v
Milvus
        |
        v
Streamlit -> retriever -> small open model -> cited answer
```

## Principles

- Ingestion keeps the URL, title, publication date, collection date, and source type.
- RAG should prefer recent, Gironde- and Landes-localized documents when the question
  requires it.
- Application components will be added step by step to keep checks fast.

## Expected services

- Airflow for hourly orchestration.
- Milvus for vector search.
- Streamlit for the v1 interface.
- A compact open model for local generation, to be selected after a small benchmark.
