# User action items

This file tracks actions that require the project owner outside the codebase.

## API accounts and keys

- [ ] Create a Météo-France API portal account: https://portail-api.meteofrance.fr/
- [ ] Request access to the real-time `DonneesPubliquesMeteoForets` API.
- [ ] Check whether the Météo-France API portal also grants access to
  `DonneesPubliquesVigilance`.
- [ ] Store the Météo-France API key locally only, never in Git.
- [ ] Add the final local variable name to `.env` once the connector defines it.
- [ ] Create an Infoclimat account/API key later if station observations become useful.

## Source review

- [ ] Review the Météo des forêts archive source with `docs/source-review-checklist.md`.
- [ ] Confirm attribution wording for Météo-France data.
- [ ] Confirm that the project can use the data under the documented open license.
- [ ] Review real-time Météo-France API quotas once the account is created.
- [ ] Review Infoclimat usage constraints before using it in automated ingestion.

## Repository administration

- [ ] Confirm `@Nhkp` is the correct GitHub owner for `.github/CODEOWNERS`.
- [ ] Confirm GitHub Actions runs successfully on `main`.
- [ ] Add repository secrets only when a connector actually needs them.
- [ ] Avoid adding API keys until there is a tested connector contract.

## Later product decisions

- [ ] Decide when raw JSONL is no longer enough and curated Parquet should be added.
- [ ] Choose the first local embedding model after chunking exists.
- [ ] Choose the first tiny/open LLM only after retrieval has test fixtures.
