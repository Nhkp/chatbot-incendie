# chatbot-incendie

![Python](https://img.shields.io/badge/python-3.11-blue)
![Coverage](https://img.shields.io/badge/coverage-%3E%3D80%25-brightgreen)
[![CI](https://github.com/Nhkp/chatbot-incendie/actions/workflows/ci.yml/badge.svg)](https://github.com/Nhkp/chatbot-incendie/actions/workflows/ci.yml)
![Code style](https://img.shields.io/badge/code%20style-ruff-black)

RAG chatbot specialized in questions about wildfires in Gironde and Landes, France, in 2026.

The project currently supports API-first ingestion, cleaning, chunking, local
embeddings, Milvus indexing, and a minimal FastAPI + Streamlit chat loop.

## Getting started

```bash
uv sync
uv run pytest
```

## Local checks

```bash
scripts/check.sh
```

Or use the Makefile shortcuts:

```bash
make check
```

## Hooks

```bash
make hooks
```

This installs both `pre-commit` and `commit-msg` hooks. Commit messages must follow
Conventional Commits.

## Local data smoke tests

Fetch the current Météo-France wildfire danger data after setting `METEO_FRANCE_API_KEY`
in the environment:

```bash
uv run python scripts/run_meteo_des_forets_realtime.py
```

Embed a generated JSONL file locally. This downloads the configured embedding model on
first run:

```bash
uv run python scripts/run_local_embedding_smoke.py data/raw/2026-07-29/meteo-des-forets-realtime.jsonl
```

Start Milvus and index the same JSONL file:

```bash
docker compose up -d
uv run python scripts/index_meteo_des_forets_milvus.py data/raw/2026-07-29/meteo-des-forets-realtime.jsonl
```

Populate every implemented API-first source and index it in Milvus:

```bash
make populate-sources
```

This currently fetches Météo des forêts, Météo-France Vigilance, NASA FIRMS, and
Géorisques, plus local media feed metadata from France 3, Actu.fr, and ici/France Bleu.
Required API keys:

- `METEO_FRANCE_API_KEY` for Météo-France APIs.
- `NASA_FIRMS_MAP_KEY` for NASA FIRMS.

Media feeds are contextual evidence only. For evacuation, return-home, road-closure, or
emergency-instruction answers, official sources must outrank media citations.

Start the local chat API and Streamlit interface:

```bash
uv run uvicorn chatbot_incendie.api:app --host 0.0.0.0 --port 8001
uv run streamlit run apps/streamlit_app.py
```

Or run the full local demo with one command:

```bash
make demo
```

This loads `.env`, starts Milvus if possible, fetches Météo-France data, indexes it,
starts FastAPI, then opens the Streamlit app.

The demo uses fast extractive answers by default:

```env
RAG_RESPONSE_MODE=extractive
```

To use the local LLM instead, set:

```env
RAG_RESPONSE_MODE=llm
LLM_MAX_NEW_TOKENS=80
```

## Documentation

- `docs/project-brief.md`: objective and v1 scope.
- `docs/architecture.md`: target architecture.
- `docs/data-sources.md`: initial registry of candidate sources.
- `docs/agents/`: work briefs for specialized agents.
- `docs/source-policy.md`: source intake and scraping policy.
- `docs/git-workflow.md`: branch, PR, and commit workflow.
