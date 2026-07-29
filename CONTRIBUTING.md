# Contributing

## Setup

```bash
uv sync
make hooks
```

## Daily workflow

```bash
make check
```

Keep pull requests small and focused. Each commit should be independent and should
follow `docs/commit-guidelines.md`.

Code changes must follow `docs/code-guidelines.md`.

## Pull requests

- Use a short-lived branch.
- Keep one intent per PR.
- Include tests for non-trivial logic.
- Update documentation when behavior, commands, or source policy changes.
- Do not include generated files, local caches, secrets, or temporary data.
