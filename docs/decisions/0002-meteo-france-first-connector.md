# 0002 - First weather connector

## Decision

The first source connector targets the archived Météo des forêts CSV data from
Météo-France, filtered to Gironde (`33`) and Landes (`40`).

## Context

Météo des forêts is official prevention data. It provides department-level wildfire
danger for J+1 and J+2, with levels from 1 to 4. The archived files are available from
2024 onward and the current-year archive is updated daily during fire season.

Real-time Météo des forêts and Vigilance APIs require authenticated access through the
Météo-France API portal, so they are deferred until credentials exist.

## Consequences

- Tests use fixture CSV strings only and never call live services.
- Raw connector output remains `RawDocument` and flows into the JSONL ingestion runner.
- The connector must not present Météo des forêts as live incident data or prediction.
- Raw JSONL remains the capture format; curated Parquet is the planned scale upgrade
  when volume or analytical querying requires it.
