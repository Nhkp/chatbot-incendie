.PHONY: sync check lint format type test hooks hooks-run clean

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

clean:
	find . -type d \( -name __pycache__ -o -name .pytest_cache -o -name .mypy_cache -o -name .ruff_cache \) -prune -exec rm -rf {} +
	rm -rf .coverage htmlcov
