# chatbot-incendie

![Python](https://img.shields.io/badge/python-3.11-blue)
![Coverage](https://img.shields.io/badge/coverage-%3E%3D80%25-brightgreen)
[![CI](https://github.com/Nhkp/chatbot-incendie/actions/workflows/ci.yml/badge.svg)](https://github.com/Nhkp/chatbot-incendie/actions/workflows/ci.yml)
![Code style](https://img.shields.io/badge/code%20style-ruff-black)

RAG chatbot specialized in questions about wildfires in Gironde and Landes, France, in 2026.

The first project step sets up the workspace: agent conventions, code quality, CI,
local hooks, and baseline documentation. The RAG application, Airflow ingestion,
Milvus, and Streamlit interface will be added later.

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

## Documentation

- `docs/project-brief.md`: objective and v1 scope.
- `docs/architecture.md`: target architecture.
- `docs/data-sources.md`: initial registry of candidate sources.
- `docs/agents/`: work briefs for specialized agents.
- `docs/source-policy.md`: source intake and scraping policy.
- `docs/git-workflow.md`: branch, PR, and commit workflow.
