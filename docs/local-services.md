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

Populate all implemented real sources and index them in Milvus with:

```bash
make populate-sources
```

The command loads `.env`, fetches official/open-data sources and local media feed
metadata, continues if one source fails, and prints per-source raw, cleaned, chunk,
and upsert counts.

Required keys:

- `METEO_FRANCE_API_KEY` for Météo-France wildfire danger and vigilance APIs.
- `NASA_FIRMS_MAP_KEY` for NASA FIRMS active fire detections.

Optional endpoint overrides:

- `METEO_FRANCE_API_BASE_URL`
- `METEO_FRANCE_VIGILANCE_API_BASE_URL`
- `GEORISQUES_API_BASE_URL`

Media feed metadata currently comes from France 3, Actu.fr, and ici/France Bleu.
These media citations are contextual; official sources remain authoritative for
safety-sensitive instructions.

## Planned services

- Airflow for hourly ingestion orchestration.
- Optional object storage for raw documents and artifacts.

## Web chat

Start the API:

```bash
uv run uvicorn chatbot_incendie.api:app --host 0.0.0.0 --port 8001
```

Start the Streamlit UI in another terminal:

```bash
uv run streamlit run apps/streamlit_app.py
```

The Streamlit app calls `CHATBOT_API_URL`, defaulting to `http://localhost:8001`.

## LLM providers

Cloud LLM generation is selected from `.env`:

```env
RAG_RESPONSE_MODE=llm
LLM_PROVIDER=gemini
LLM_MODEL_NAME=gemini-3.6-flash
LLM_MAX_NEW_TOKENS=120
LLM_TEMPERATURE=0
GEMINI_API_KEY=your-key
```

Supported `LLM_PROVIDER` values are `local`, `gemini`, `mistral`, `deepseek`,
`openai`, and `anthropic`. Set only the matching key:

- `GEMINI_API_KEY`
- `MISTRAL_API_KEY`
- `DEEPSEEK_API_KEY`
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`

Use `RAG_RESPONSE_MODE=extractive` for fast local testing without any LLM provider.
