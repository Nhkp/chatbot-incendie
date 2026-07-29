# Away work plan

Use this plan while the project owner is away. The goal is to keep making useful
progress without requiring API keys, live network access, or product decisions.

## Guardrails

- Do not add Airflow, Milvus, Streamlit, embeddings, or LLM dependencies.
- Do not call live APIs in tests.
- Do not implement scraping.
- Keep JSONL as the raw ingestion format.
- Keep Parquet as the planned curated-data upgrade path, not part of this slice.
- Keep each change small enough for an independent Conventional Commit.

## Primary implementation slice

Build an offline-testable connector foundation for Météo des forêts archive data.

Implementation targets:

- Add a `connectors` module with:
  - `HttpClient` protocol;
  - `SourceConnector` protocol;
  - a small `StaticTextClient` or test-only fake client if useful for tests.
- Add a `MeteoDesForetsArchiveConnector` that:
  - accepts CSV text from an injected client or parser function;
  - parses the documented columns `Reference_time`, `dep_code`, `niveau_j1`,
    `niveau_j2`, and `nom_dep`;
  - keeps only departments `33` and `40`;
  - returns `RawDocument` instances;
  - does not know anything about Airflow or Milvus.
- Add a parser helper if it keeps the connector boring and testable.

Expected commit:

```text
feat(connectors): add Meteo des forets archive parser
```

## Test cases

- Valid row for department `33` creates one `RawDocument`.
- Valid row for department `40` creates one `RawDocument`.
- Department outside `33` and `40` is ignored.
- Missing required CSV column raises `ValueError`.
- Invalid danger level raises `ValueError`.
- Connector output can be passed to `run_ingestion(...)` and written to JSONL.
- Tests use fixture strings only and make no network calls.

## Documentation updates

- Add a decision record for Météo des forêts archive as the first connector.
- Mention that real-time Météo-France APIs are deferred until the API key exists.
- Mention that Météo des forêts is prevention/risk-context data, not a live incident
  source and not a fire prediction source.
- Record the Parquet upgrade path: raw JSONL first, curated Parquet when scale or
  analytical querying requires it.

Expected commit:

```text
docs: document Meteo-France connector decision
```

## Validation

Run before finishing:

```bash
make check
uv run pre-commit run --all-files
git status --short --branch
```

If implementation is completed and checks pass, commit locally. Push only if the branch
is still aligned with `origin/main`.
