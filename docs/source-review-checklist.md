# Source review checklist

Use this checklist before implementing any API connector or scraper.

## Identity

- Source name:
- Source owner:
- Source URL:
- Source type: official, open data, news, weather, other.
- Intended V1 use:

## Legal and access review

- Usage terms were checked.
- robots.txt was checked when scraping is considered.
- API documentation was checked when an API exists.
- Attribution requirements are understood.
- Paid, private, or login-only data is excluded.

## Technical review

- API is preferred over scraping when available.
- Expected update frequency is known.
- Conservative rate limit is documented.
- Required request headers or user agent are documented.
- Error, throttling, and access-denial behavior is understood.

## Data quality review

- Documents include a stable source URL.
- Publication date is available or a fallback is documented.
- Content is relevant to Gironde or Landes wildfires, or useful local context.
- Deduplication can use canonical URL, content fingerprint, or both.
- The source can be disabled without breaking the pipeline.

## Approval

- Status in `docs/data-sources.md` is updated.
- Usage notes are documented.
- Rate-limit notes are documented.
- The first connector test will not call the live network in CI.
