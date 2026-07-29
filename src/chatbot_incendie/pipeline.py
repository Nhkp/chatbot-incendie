from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from chatbot_incendie.cleaning import clean_and_deduplicate
from chatbot_incendie.connectors import SourceConnector
from chatbot_incendie.domain import RawDocument, Source
from chatbot_incendie.ingestion import run_ingestion


@dataclass(frozen=True)
class PipelineResult:
    source_id: str
    input_count: int
    output_count: int
    duplicate_count: int
    rejected_count: int
    output_path: Path
    collected_at: datetime


def run_clean_ingestion_pipeline(
    source: Source,
    connector: SourceConnector,
    output_dir: Path,
    collected_at: datetime | None = None,
) -> PipelineResult:
    raw_documents = connector.fetch(source)
    _validate_source_documents(source, raw_documents)
    cleaned_batch = clean_and_deduplicate(raw_documents)
    ingestion_result = run_ingestion(
        source=source,
        collector=_MemoryCollector(cleaned_batch.documents),
        output_dir=output_dir,
        collected_at=collected_at,
    )
    return PipelineResult(
        source_id=source.id,
        input_count=cleaned_batch.input_count,
        output_count=ingestion_result.document_count,
        duplicate_count=cleaned_batch.duplicate_count,
        rejected_count=cleaned_batch.rejected_count,
        output_path=ingestion_result.output_path,
        collected_at=ingestion_result.collected_at,
    )


@dataclass(frozen=True)
class _MemoryCollector:
    documents: list[RawDocument]

    def fetch(self) -> list[RawDocument]:
        return self.documents


def _validate_source_documents(source: Source, documents: list[RawDocument]) -> None:
    mismatched_ids = sorted(
        {document.source_id for document in documents if document.source_id != source.id}
    )
    if mismatched_ids:
        ids = ", ".join(mismatched_ids)
        raise ValueError(
            f"connector returned documents for unexpected source ids: {ids}; expected: {source.id}"
        )
