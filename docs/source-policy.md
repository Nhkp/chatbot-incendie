# Source policy

## Intake rules

- Prefer official sources and documented APIs.
- Prefer APIs over scraping.
- Do not automate a source until its legal and technical status is clear.
- Record each candidate source in `docs/data-sources.md`.
- Keep the source URL, canonical URL when available, title, publication date,
  collection date, and source type.

## Scraping rules

- Respect terms of service.
- Respect robots.txt when applicable.
- Use conservative rate limits.
- Identify the project clearly when a source requires a user agent.
- Stop or back off on repeated errors, throttling, or access denials.

## Data quality rules

- Deduplicate by canonical URL first, then by content fingerprint.
- Isolate empty, very short, malformed, or off-topic documents.
- Keep enough metadata to explain why a document was ingested.

## Safety rules

- Do not present scraped or generated content as official emergency advice.
- Prefer official emergency sources for safety-critical answers.
- Preserve citations so the user can inspect the underlying source.
