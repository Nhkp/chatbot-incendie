from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from chatbot_incendie.domain import RawDocument, Source
from chatbot_incendie.jsonl_store import with_collected_at, write_raw_documents


class DocumentCollector(Protocol):
    def fetch(self) -> list[RawDocument]: ...


@dataclass(frozen=True)
class IngestionResult:
    source_id: str
    document_count: int
    output_path: Path
    collected_at: datetime


def run_ingestion(
    source: Source,
    collector: DocumentCollector,
    output_dir: Path = Path("data/raw"),
    collected_at: datetime | None = None,
) -> IngestionResult:
    collected = collected_at or datetime.now(UTC)
    documents = [with_collected_at(document, collected) for document in collector.fetch()]
    output_path = output_dir / collected.date().isoformat() / f"{source.id}.jsonl"
    document_count = write_raw_documents(output_path, documents)
    return IngestionResult(
        source_id=source.id,
        document_count=document_count,
        output_path=output_path,
        collected_at=collected,
    )
