#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

API_HOST="${API_HOST:-0.0.0.0}"
API_PORT="${API_PORT:-8001}"
API_PID=""

cleanup() {
  if [[ -n "${API_PID}" ]] && kill -0 "${API_PID}" 2>/dev/null; then
    kill "${API_PID}"
    wait "${API_PID}" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
fi

echo "Starting Milvus if needed..."
if ! docker compose up -d; then
  echo "docker compose up failed. If port 19530 is already used by another Milvus, reusing it."
fi

echo "Fetching and indexing all implemented sources into Milvus..."
uv run python scripts/populate_sources.py

echo "Starting FastAPI on http://localhost:${API_PORT}..."
uv run uvicorn chatbot_incendie.api:app --host "${API_HOST}" --port "${API_PORT}" &
API_PID="$!"

sleep 3
if ! kill -0 "${API_PID}" 2>/dev/null; then
  echo "FastAPI failed to start."
  exit 2
fi

export CHATBOT_API_URL="${CHATBOT_API_URL:-http://localhost:${API_PORT}}"
echo "Starting Streamlit. Press Ctrl+C to stop the demo."
uv run streamlit run apps/streamlit_app.py
