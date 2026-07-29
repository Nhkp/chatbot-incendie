from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from chatbot_incendie.connectors import (
    MeteoDesForetsArchiveConnector,
    parse_meteo_des_forets_archive,
)
from chatbot_incendie.domain import RawDocument, Source, SourceStatus, SourceType
from chatbot_incendie.ingestion import run_ingestion
from chatbot_incendie.jsonl_store import read_raw_documents


@dataclass(frozen=True)
class FakeTextClient:
    text: str

    def get_text(self, url: str) -> str:
        return self.text


@dataclass(frozen=True)
class DocumentsCollector:
    documents: list[RawDocument]

    def fetch(self) -> list[RawDocument]:
        return self.documents


def test_meteo_des_forets_parser_keeps_gironde_and_landes() -> None:
    documents = parse_meteo_des_forets_archive(_csv(), _source(), "https://example.com/mdf.csv")

    assert [document.title for document in documents] == [
        "Meteo des forets 33 - 2026-07-29T17:00:00+00:00",
        "Meteo des forets 40 - 2026-07-29T17:00:00+00:00",
    ]
    assert all("source Meteo-France" in document.content for document in documents)


def test_meteo_des_forets_parser_ignores_other_departments() -> None:
    documents = parse_meteo_des_forets_archive(_csv(), _source(), "https://example.com/mdf.csv")

    assert all("Departement 24" not in document.content for document in documents)


def test_meteo_des_forets_parser_accepts_semicolon_csv() -> None:
    csv_text = (
        "Reference_time;dep_code;niveau_j1;niveau_j2;nom_dep\n"
        "2026-07-29T17:00:00+00:00;33;3;4;Gironde\n"
    )

    documents = parse_meteo_des_forets_archive(csv_text, _source(), "https://example.com/mdf.csv")

    assert len(documents) == 1


def test_meteo_des_forets_parser_rejects_missing_required_column() -> None:
    csv_text = "Reference_time,dep_code,niveau_j1,nom_dep\n2026-07-29T17:00:00+00:00,33,3,Gironde\n"

    with pytest.raises(ValueError, match="missing required fields: niveau_j2"):
        parse_meteo_des_forets_archive(csv_text, _source(), "https://example.com/mdf.csv")


def test_meteo_des_forets_parser_rejects_invalid_danger_level() -> None:
    csv_text = (
        "Reference_time,dep_code,niveau_j1,niveau_j2,nom_dep\n"
        "2026-07-29T17:00:00+00:00,33,5,4,Gironde\n"
    )

    with pytest.raises(ValueError, match="danger level must be 1, 2, 3, or 4"):
        parse_meteo_des_forets_archive(csv_text, _source(), "https://example.com/mdf.csv")


def test_meteo_des_forets_connector_integrates_with_ingestion(tmp_path: Path) -> None:
    source = _source()
    connector = MeteoDesForetsArchiveConnector(
        client=FakeTextClient(_csv()),
        archive_url="https://example.com/mdf.csv",
    )
    documents = connector.fetch(source)

    result = run_ingestion(
        source=source,
        collector=DocumentsCollector(documents),
        output_dir=tmp_path,
        collected_at=datetime(2026, 7, 29, 18, 0, tzinfo=UTC),
    )

    assert result.document_count == 2
    assert [document.source_id for document in read_raw_documents(result.output_path)] == [
        "meteo-des-forets-archive",
        "meteo-des-forets-archive",
    ]


def _csv() -> str:
    return (
        "Reference_time,dep_code,niveau_j1,niveau_j2,nom_dep\n"
        "2026-07-29T17:00:00+00:00,33,3,4,Gironde\n"
        "2026-07-29T17:00:00+00:00,40,4,4,Landes\n"
        "2026-07-29T17:00:00+00:00,24,2,3,Dordogne\n"
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
