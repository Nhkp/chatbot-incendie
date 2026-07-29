from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Any

from chatbot_incendie.domain import RawDocument


def write_raw_documents(path: Path, documents: Iterable[RawDocument]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as file:
        for document in documents:
            file.write(json.dumps(_raw_document_to_json(document), ensure_ascii=False))
            file.write("\n")
            count += 1
    return count


def read_raw_documents(path: Path) -> list[RawDocument]:
    documents: list[RawDocument] = []
    with path.open(encoding="utf-8") as file:
        for line in file:
            if line.strip():
                documents.append(_raw_document_from_json(json.loads(line)))
    return documents


def with_collected_at(document: RawDocument, collected_at: datetime) -> RawDocument:
    if document.collected_at is not None:
        return document
    return replace(document, collected_at=collected_at)


def _raw_document_to_json(document: RawDocument) -> dict[str, str | None]:
    return {
        "source_id": document.source_id,
        "url": document.url,
        "canonical_url": document.canonical_url,
        "title": document.title,
        "content": document.content,
        "published_at": _datetime_to_json(document.published_at),
        "collected_at": _datetime_to_json(document.collected_at),
    }


def _raw_document_from_json(data: dict[str, Any]) -> RawDocument:
    return RawDocument(
        source_id=_as_text(data, "source_id"),
        url=_as_text(data, "url"),
        canonical_url=_as_optional_text(data, "canonical_url"),
        title=_as_optional_text(data, "title"),
        content=_as_text(data, "content"),
        published_at=_datetime_from_json(_as_optional_text(data, "published_at")),
        collected_at=_datetime_from_json(_as_optional_text(data, "collected_at")),
    )


def _datetime_to_json(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _datetime_from_json(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value is not None else None


def _as_text(data: dict[str, Any], field: str) -> str:
    value = data[field]
    if not isinstance(value, str):
        raise ValueError(f"JSONL field must be a string: {field}")
    return value


def _as_optional_text(data: dict[str, Any], field: str) -> str | None:
    value = data[field]
    if value is None or isinstance(value, str):
        return value
    raise ValueError(f"JSONL field must be a string or null: {field}")
