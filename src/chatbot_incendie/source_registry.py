from __future__ import annotations

import tomllib
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from chatbot_incendie.domain import Source, SourceStatus, SourceType

REQUIRED_SOURCE_FIELDS = {
    "id",
    "name",
    "type",
    "url",
    "status",
    "usage_notes",
    "rate_limit_notes",
}


def load_sources(path: Path) -> list[Source]:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    entries = data.get("sources")
    if not isinstance(entries, list):
        raise ValueError("sources.toml must contain a [[sources]] array")

    sources = [_source_from_mapping(entry) for entry in entries]
    _ensure_unique_ids(sources)
    return sources


def get_source_by_id(sources: Sequence[Source], source_id: str) -> Source | None:
    return next((source for source in sources if source.id == source_id), None)


def _source_from_mapping(entry: object) -> Source:
    if not isinstance(entry, dict):
        raise ValueError("each source entry must be a table")

    missing_fields = REQUIRED_SOURCE_FIELDS - entry.keys()
    if missing_fields:
        missing = ", ".join(sorted(missing_fields))
        raise ValueError(f"source entry is missing required fields: {missing}")

    return Source(
        id=_as_text(entry, "id"),
        name=_as_text(entry, "name"),
        type=SourceType(_as_text(entry, "type")),
        url=_as_text(entry, "url"),
        status=SourceStatus(_as_text(entry, "status")),
        usage_notes=_as_text(entry, "usage_notes"),
        rate_limit_notes=_as_text(entry, "rate_limit_notes"),
    )


def _as_text(entry: dict[str, Any], field: str) -> str:
    value = entry[field]
    if not isinstance(value, str):
        raise ValueError(f"source field must be a string: {field}")
    return value


def _ensure_unique_ids(sources: Sequence[Source]) -> None:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for source in sources:
        if source.id in seen:
            duplicates.add(source.id)
        seen.add(source.id)
    if duplicates:
        ids = ", ".join(sorted(duplicates))
        raise ValueError(f"source ids must be unique: {ids}")
