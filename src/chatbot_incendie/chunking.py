from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from itertools import pairwise

from chatbot_incendie.domain import RawDocument

DEFAULT_MAX_CHARS = 800
DEFAULT_OVERLAP_CHARS = 120


@dataclass(frozen=True)
class Chunk:
    source_id: str
    document_url: str
    canonical_url: str | None
    title: str | None
    content: str
    chunk_index: int
    chunk_count: int
    published_at: datetime | None
    collected_at: datetime | None


def chunk_document(
    document: RawDocument,
    max_chars: int = DEFAULT_MAX_CHARS,
    overlap_chars: int = DEFAULT_OVERLAP_CHARS,
) -> list[Chunk]:
    _validate_chunk_config(max_chars, overlap_chars)
    target_chars = max_chars - overlap_chars if overlap_chars else max_chars
    parts = _split_text(document.content, target_chars)
    windows = _with_overlap(parts, overlap_chars)
    chunk_count = len(windows)
    return [
        Chunk(
            source_id=document.source_id,
            document_url=document.url,
            canonical_url=document.canonical_url,
            title=document.title,
            content=content,
            chunk_index=index,
            chunk_count=chunk_count,
            published_at=document.published_at,
            collected_at=document.collected_at,
        )
        for index, content in enumerate(windows)
    ]


def chunk_documents(
    documents: Iterable[RawDocument],
    max_chars: int = DEFAULT_MAX_CHARS,
    overlap_chars: int = DEFAULT_OVERLAP_CHARS,
) -> list[Chunk]:
    chunks: list[Chunk] = []
    for document in documents:
        chunks.extend(chunk_document(document, max_chars, overlap_chars))
    return chunks


def _validate_chunk_config(max_chars: int, overlap_chars: int) -> None:
    if max_chars <= 0:
        raise ValueError("max_chars must be greater than 0")
    if overlap_chars < 0 or overlap_chars >= max_chars:
        raise ValueError("overlap_chars must be greater than or equal to 0 and less than max_chars")


def _split_text(text: str, max_chars: int) -> list[str]:
    paragraphs = [paragraph.strip() for paragraph in text.split("\n\n") if paragraph.strip()]
    if not paragraphs:
        raise ValueError("document content must not be empty")

    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        for part in _split_paragraph(paragraph, max_chars):
            candidate = f"{current}\n\n{part}" if current else part
            if len(candidate) <= max_chars:
                current = candidate
                continue
            if current:
                chunks.append(current)
            current = part
    if current:
        chunks.append(current)
    return chunks


def _split_paragraph(paragraph: str, max_chars: int) -> list[str]:
    if len(paragraph) <= max_chars:
        return [paragraph]

    words = paragraph.split()
    parts: list[str] = []
    current = ""
    for word in words:
        if len(word) > max_chars:
            if current:
                parts.append(current)
                current = ""
            parts.extend(_split_long_word(word, max_chars))
            continue
        candidate = f"{current} {word}" if current else word
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current:
            parts.append(current)
        current = word
    if current:
        parts.append(current)
    return parts


def _split_long_word(word: str, max_chars: int) -> list[str]:
    return [word[index : index + max_chars] for index in range(0, len(word), max_chars)]


def _with_overlap(chunks: list[str], overlap_chars: int) -> list[str]:
    if overlap_chars == 0 or len(chunks) <= 1:
        return chunks

    overlapped = [chunks[0]]
    for previous, current in pairwise(chunks):
        overlap = previous[-overlap_chars:]
        overlapped.append(f"{overlap}{current}")
    return overlapped
