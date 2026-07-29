.PHONY: sync check lint format type test hooks hooks-run demo demo-data populate-sources api ui clean

sync:
	uv sync

check:
	scripts/check.sh

lint:
	uv run ruff check .

format:
	uv run ruff format .

type:
	uv run mypy src tests

test:
	uv run pytest

hooks:
	uv run pre-commit install --hook-type pre-commit --hook-type commit-msg

hooks-run:
	uv run pre-commit run --all-files

demo:
	scripts/run_demo.sh

demo-data:
	set -a; [ ! -f .env ] || . ./.env; set +a; \
	docker compose up -d || true; \
	uv run python scripts/run_meteo_des_forets_realtime.py; \
	uv run python scripts/index_meteo_des_forets_milvus.py data/raw/$$(date +%F)/meteo-des-forets-realtime.jsonl

populate-sources:
	uv run python scripts/populate_sources.py

api:
	uv run uvicorn chatbot_incendie.api:app --host 0.0.0.0 --port 8001

ui:
	uv run streamlit run apps/streamlit_app.py

clean:
	find . -type d \( -name __pycache__ -o -name .pytest_cache -o -name .mypy_cache -o -name .ruff_cache \) -prune -exec rm -rf {} +
	rm -rf .coverage htmlcov
