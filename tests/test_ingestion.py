from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from chatbot_incendie.domain import RawDocument, Source, SourceStatus, SourceType
from chatbot_incendie.ingestion import run_ingestion
from chatbot_incendie.jsonl_store import read_raw_documents


@dataclass(frozen=True)
class FakeCollector:
    documents: list[RawDocument]

    def fetch(self) -> list[RawDocument]:
        return self.documents


def test_run_ingestion_writes_documents_and_reports_result(tmp_path: Path) -> None:
    source = _source()
    collected_at = datetime(2026, 7, 29, 14, 0, tzinfo=UTC)
    collector = FakeCollector(
        [
            RawDocument(
                source_id=source.id,
                url="https://example.com/doc",
                title="Situation update",
                content="Sourced update.",
            )
        ]
    )

    result = run_ingestion(source, collector, tmp_path, collected_at)

    assert result.source_id == source.id
    assert result.document_count == 1
    assert result.collected_at == collected_at
    assert result.output_path == tmp_path / "2026-07-29" / "sdis-33.jsonl"
    assert result.output_path.exists()
    assert read_raw_documents(result.output_path)[0].collected_at == collected_at


def test_run_ingestion_preserves_existing_collected_at(tmp_path: Path) -> None:
    source = _source()
    existing_collected_at = datetime(2026, 7, 28, 10, 0, tzinfo=UTC)
    run_collected_at = datetime(2026, 7, 29, 14, 0, tzinfo=UTC)
    collector = FakeCollector(
        [
            RawDocument(
                source_id=source.id,
                url="https://example.com/doc",
                content="Sourced update.",
                collected_at=existing_collected_at,
            )
        ]
    )

    result = run_ingestion(source, collector, tmp_path, run_collected_at)

    assert read_raw_documents(result.output_path)[0].collected_at == existing_collected_at


def test_run_ingestion_writes_empty_jsonl_for_empty_collector(tmp_path: Path) -> None:
    source = _source()
    collected_at = datetime(2026, 7, 29, 14, 0, tzinfo=UTC)

    result = run_ingestion(source, FakeCollector([]), tmp_path, collected_at)

    assert result.document_count == 0
    assert result.output_path.exists()
    assert result.output_path.read_text(encoding="utf-8") == ""


def _source() -> Source:
    return Source(
        id="sdis-33",
        name="SDIS 33",
        type=SourceType.OFFICIAL_WEBSITE,
        url="https://www.sdis33.fr/",
        status=SourceStatus.CANDIDATE,
        usage_notes="Public operational information.",
        rate_limit_notes="Conservative polling.",
    )
