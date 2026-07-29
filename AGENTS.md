# Agent instructions for chatbot-incendie

This repository builds a RAG chatbot specialized in wildfires in Gironde and Landes, France, in
2026. Agents must favor short, verified, useful changes.

## Working rules

- Read the real flow before changing code.
- Reuse existing tools, patterns, and helpers before creating new ones.
- Do not add dependencies without a clear reason.
- Keep diffs small and centered on the request.
- Add a runnable test for any non-trivial logic.
- Follow the code guidelines in `docs/code-guidelines.md`.
- Never commit secrets, local dumps, API tokens, or sensitive data.
- Follow the commit rules in `docs/commit-guidelines.md`.
- Follow the Git workflow in `docs/git-workflow.md`.
- Follow the source intake rules in `docs/source-policy.md`.
- Document structural decisions in `docs/decisions/`.

## Expected commands

```bash
uv sync
uv run ruff check .
uv run ruff format --check .
uv run mypy src tests
uv run pytest
```

Use `make check` as the preferred shortcut when `make` is available.

## Agent boundaries

- Agents must not invent official sources: every data source must be tracked in
  `docs/data-sources.md`.
- Scrapers must respect terms of service, robots.txt when applicable, and rate limits.
- RAG answers must cite the sources used as soon as the product exposes citations.
- Intentional shortcuts must be marked with a `ponytail:` comment that names the limit
  and the upgrade path.
