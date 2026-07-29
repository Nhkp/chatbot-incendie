from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from chatbot_incendie.connectors import MeteoDesForetsArchiveConnector
from chatbot_incendie.domain import RawDocument, Source, SourceStatus, SourceType
from chatbot_incendie.jsonl_store import read_raw_documents
from chatbot_incendie.pipeline import run_clean_ingestion_pipeline


@dataclass(frozen=True)
class FakeConnector:
    documents: list[RawDocument]

    def fetch(self, source: Source) -> list[RawDocument]:
        return self.documents


@dataclass(frozen=True)
class FakeTextClient:
    text: str

    def get_text(self, url: str) -> str:
        return self.text


def test_clean_ingestion_pipeline_writes_deduplicated_documents(tmp_path: Path) -> None:
    source = _source()
    collected_at = datetime(2026, 7, 29, 18, 0, tzinfo=UTC)
    connector = FakeConnector(
        [
            RawDocument(source_id=source.id, url="https://example.com/a", content="  A  "),
            RawDocument(source_id=source.id, url="https://example.com/b", content="B"),
            RawDocument(source_id=source.id, url="https://example.com/a-copy", content="A"),
        ]
    )

    result = run_clean_ingestion_pipeline(source, connector, tmp_path, collected_at)
    written_documents = read_raw_documents(result.output_path)

    assert result.source_id == source.id
    assert result.input_count == 3
    assert result.output_count == 2
    assert result.duplicate_count == 1
    assert result.rejected_count == 0
    assert result.collected_at == collected_at
    assert result.output_path == tmp_path / "2026-07-29" / f"{source.id}.jsonl"
    assert [document.content for document in written_documents] == ["A", "B"]


def test_meteo_des_forets_connector_runs_through_clean_ingestion_pipeline(
    tmp_path: Path,
) -> None:
    source = _source()
    connector = MeteoDesForetsArchiveConnector(
        client=FakeTextClient(_meteo_des_forets_csv()),
        archive_url="https://example.com/mdf.csv",
    )

    result = run_clean_ingestion_pipeline(
        source=source,
        connector=connector,
        output_dir=tmp_path,
        collected_at=datetime(2026, 7, 29, 18, 0, tzinfo=UTC),
    )
    written_documents = read_raw_documents(result.output_path)

    assert result.input_count == 2
    assert result.output_count == 2
    assert [document.title for document in written_documents] == [
        "Meteo des forets 33 - 2026-07-29T17:00:00+00:00",
        "Meteo des forets 40 - 2026-07-29T17:00:00+00:00",
    ]


def _meteo_des_forets_csv() -> str:
    return (
        "Reference_time,dep_code,niveau_j1,niveau_j2,nom_dep\n"
        "2026-07-29T17:00:00+00:00,33,3,4,Gironde\n"
        "2026-07-29T17:00:00+00:00,40,4,4,Landes\n"
    )


def _source() -> Source:
    return Source(
        id="meteo-des-forets-archive",
        name="Meteo des forets archive",
        type=SourceType.OPEN_DATA,
        url="https://www.data.gouv.fr/datasets/archives-de-la-meteo-des-forets",
        status=SourceStatus.APPROVED,
        usage_notes="Open archive data for wildfire danger prevention context.",
        rate_limit_notes="Download archive files conservatively.",
    )
