# User action items

This file tracks actions that require the project owner outside the codebase.

## API accounts and keys

- [X] Create a Météo-France API portal account: https://portail-api.meteofrance.fr/
- [X] Request access to the real-time `DonneesPubliquesMeteoForets` API.
- [X] Check whether the Météo-France API portal also grants access to
  `DonneesPubliquesVigilance`.
- [X] Store the Météo-France API key locally only, never in Git.
- [X] Add the final local variable name to `.env` once the connector defines it.
- [ ] Create an Infoclimat account/API key later if station observations become useful.

## Source review

- [ ] Review the Météo des forêts archive source with `docs/source-review-checklist.md`.
- [ ] Confirm attribution wording for Météo-France data.
- [ ] Confirm that the project can use the data under the documented open license.
- [ ] Review real-time Météo-France API quotas once the account is created.
- [ ] Review Infoclimat usage constraints before using it in automated ingestion.

## Repository administration

- [X] Confirm `@Nhkp` is the correct GitHub owner for `.github/CODEOWNERS`.
- [X] Confirm GitHub Actions runs successfully on `main`.
- [ ] Create the GitHub labels used by Dependabot: `dependencies` and `ci`.
- [X] Check whether merged Dependabot PRs closed automatically; close any stale PRs if
  GitHub leaves them open.
- [ ] Add repository secrets only when a connector actually needs them.
- [ ] Avoid adding API keys until there is a tested connector contract.

## Later product decisions

- [ ] Decide when raw JSONL is no longer enough and curated Parquet should be added.
- [ ] Choose the first local embedding model after chunking exists.
- [ ] Choose the first tiny/open LLM only after retrieval has test fixtures.
