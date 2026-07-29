# Ingestion agent

## Mission

Build the hourly Airflow pipeline that collects, cleans, and prepares documents for
RAG indexing.

## Rules

- Prefer a documented free API over a scraper.
- Scrape only if usage terms and rate limits allow it.
- Store the publication date, collection date, URL, and source type.
- Make each task idempotent to avoid hourly duplicates.
