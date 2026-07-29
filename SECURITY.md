# Security policy

## Supported versions

Only the `main` branch is supported while the project is in early development.

## Reporting a vulnerability

Open a private security advisory on GitHub when the repository is available. Until
then, report vulnerabilities directly to the project maintainer outside public issues.

## Project-specific rules

- Never commit secrets, API keys, local dumps, tokens, or credentials.
- Do not store raw private data in the repository.
- Treat emergency and wildfire information as sensitive: generated answers must not
  replace official emergency instructions.
- Scraping code must respect source terms, rate limits, and applicable access rules.
- Any source used by ingestion must be documented in `docs/data-sources.md`.
