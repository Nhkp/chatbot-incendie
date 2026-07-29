from __future__ import annotations

import hashlib
import re
from collections.abc import Sequence
from dataclasses import dataclass

from chatbot_incendie.domain import RawDocument


@dataclass(frozen=True)
class CleanedBatch:
    documents: list[RawDocument]
    input_count: int
    output_count: int
    duplicate_count: int
    rejected_count: int


def clean_document(document: RawDocument) -> RawDocument:
    content = _normalize_whitespace(document.content)
    title = _normalize_optional_text(document.title)
    canonical_url = document.canonical_url or document.url
    return RawDocument(
        source_id=document.source_id,
        url=document.url,
        canonical_url=canonical_url,
        title=title,
        content=content,
        published_at=document.published_at,
        collected_at=document.collected_at,
    )


def deduplicate_documents(documents: Sequence[RawDocument]) -> list[RawDocument]:
    seen_urls: set[str] = set()
    seen_fingerprints: set[str] = set()
    deduplicated: list[RawDocument] = []

    for document in documents:
        canonical_url = document.canonical_url or document.url
        fingerprint = _content_fingerprint(document.content)
        if canonical_url in seen_urls or fingerprint in seen_fingerprints:
            continue
        seen_urls.add(canonical_url)
        seen_fingerprints.add(fingerprint)
        deduplicated.append(document)

    return deduplicated


def clean_and_deduplicate(documents: Sequence[RawDocument]) -> CleanedBatch:
    cleaned: list[RawDocument] = []
    rejected_count = 0

    for document in documents:
        try:
            cleaned.append(clean_document(document))
        except ValueError:
            rejected_count += 1

    deduplicated = deduplicate_documents(cleaned)
    return CleanedBatch(
        documents=deduplicated,
        input_count=len(documents),
        output_count=len(deduplicated),
        duplicate_count=len(cleaned) - len(deduplicated),
        rejected_count=rejected_count,
    )


def _normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = _normalize_whitespace(value)
    return normalized or None


def _content_fingerprint(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()
