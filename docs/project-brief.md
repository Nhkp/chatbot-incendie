# Project brief

## Objective

Build a RAG chatbot that can answer questions about wildfires in Gironde and Landes,
France, in 2026, with answers backed by fresh sources.

## V1 scope

- Streamlit web interface.
- Context search through embeddings stored in Milvus.
- Generation with a small open model that can run locally.
- Hourly ingestion pipeline orchestrated by Airflow.
- Collection from free APIs and authorized web news sources.
- French user questions.
- French answers with cited sources.
- Gironde and Landes only focus.
- 2026-only focus.

## Initial non-goals

- Wildfire prediction.
- Personalized emergency advice.
- Replacing official emergency instructions or alerts.
- Paid data or sources without clear usage rights.
- Production high availability.

## Constraints

- Python 3.11.
- Minimum test coverage: 80%.
- Source traceability is mandatory for ingestion and RAG answers.
- If retrieved context is missing or weak, the chatbot must say it does not know and
  point users to official sources.
