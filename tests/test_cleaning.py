from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from chatbot_incendie.cleaning import (
    clean_and_deduplicate,
    clean_document,
    deduplicate_documents,
)
from chatbot_incendie.connectors import MeteoDesForetsArchiveConnector
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


def test_clean_document_normalizes_content_and_title() -> None:
    document = clean_document(
        RawDocument(
            source_id="source",
            url="https://example.com/doc",
            title="  Situation\n update  ",
            content="  First\t\tline.\n\nSecond   line.  ",
        )
    )

    assert document.title == "Situation update"
    assert document.content == "First line. Second line."


def test_clean_document_fills_missing_canonical_url() -> None:
    document = clean_document(
        RawDocument(source_id="source", url="https://example.com/doc", content="Content")
    )

    assert document.canonical_url == "https://example.com/doc"


def test_clean_document_rejects_content_that_becomes_empty() -> None:
    with pytest.raises(ValueError, match="document content must not be empty"):
        clean_document(RawDocument(source_id="source", url="https://example.com/doc", content="\n"))


def test_deduplicate_documents_keeps_first_canonical_url() -> None:
    documents = [
        _document(url="https://example.com/a", canonical_url="https://example.com/canonical"),
        _document(
            url="https://mirror.example.com/a", canonical_url="https://example.com/canonical"
        ),
    ]

    assert deduplicate_documents(documents) == [documents[0]]


def test_deduplicate_documents_keeps_first_content_fingerprint() -> None:
    documents = [
        _document(url="https://example.com/a", content="Same content"),
        _document(url="https://example.com/b", content="Same content"),
    ]

    assert deduplicate_documents(documents) == [documents[0]]


def test_deduplicate_documents_preserves_distinct_documents_order() -> None:
    documents = [
        _document(url="https://example.com/a", content="A"),
        _document(url="https://example.com/b", content="B"),
        _document(url="https://example.com/c", content="C"),
    ]

    assert deduplicate_documents(documents) == documents


def test_clean_and_deduplicate_reports_counts() -> None:
    documents = [
        _document(url="https://example.com/a", content="A"),
        _document(url="https://example.com/a-copy", content="A"),
    ]

    batch = clean_and_deduplicate(documents)

    assert batch.input_count == 2
    assert batch.output_count == 1
    assert batch.duplicate_count == 1
    assert batch.rejected_count == 0


def test_connector_cleaning_and_ingestion_flow(tmp_path: Path) -> None:
    source = _source()
    connector = MeteoDesForetsArchiveConnector(
        client=FakeTextClient(_csv()),
        archive_url="https://example.com/mdf.csv",
    )
    batch = clean_and_deduplicate(connector.fetch(source))

    result = run_ingestion(
        source=source,
        collector=DocumentsCollector(batch.documents),
        output_dir=tmp_path,
        collected_at=datetime(2026, 7, 29, 18, 0, tzinfo=UTC),
    )

    assert batch.output_count == 2
    assert result.document_count == 2
    assert all(
        document.canonical_url is not None for document in read_raw_documents(result.output_path)
    )


def _document(
    *,
    url: str,
    content: str = "Content",
    canonical_url: str | None = None,
) -> RawDocument:
    return RawDocument(
        source_id="source",
        url=url,
        canonical_url=canonical_url,
        content=content,
    )


def _csv() -> str:
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
