from datetime import UTC, datetime
from pathlib import Path

import pytest

from chatbot_incendie.domain import RawDocument
from chatbot_incendie.jsonl_store import read_raw_documents, write_raw_documents


def test_write_raw_documents_writes_one_line_per_document(tmp_path: Path) -> None:
    path = tmp_path / "raw.jsonl"
    documents = [
        RawDocument(source_id="sdis-33", url="https://example.com/1", content="First"),
        RawDocument(source_id="sdis-33", url="https://example.com/2", content="Second"),
    ]

    count = write_raw_documents(path, documents)

    assert count == 2
    assert len(path.read_text(encoding="utf-8").splitlines()) == 2


def test_raw_documents_round_trip_through_jsonl(tmp_path: Path) -> None:
    path = tmp_path / "raw.jsonl"
    published_at = datetime(2026, 7, 29, 12, 30, tzinfo=UTC)
    collected_at = datetime(2026, 7, 29, 13, 0, tzinfo=UTC)
    document = RawDocument(
        source_id="sdis-40",
        url="https://example.com/article",
        canonical_url="https://example.com/article",
        title="Situation update",
        content="Sourced content.",
        published_at=published_at,
        collected_at=collected_at,
    )

    write_raw_documents(path, [document])

    assert read_raw_documents(path) == [document]


def test_raw_documents_serialize_datetimes_as_iso_strings(tmp_path: Path) -> None:
    path = tmp_path / "raw.jsonl"
    collected_at = datetime(2026, 7, 29, 13, 0, tzinfo=UTC)
    document = RawDocument(
        source_id="sdis-40",
        url="https://example.com/article",
        content="Sourced content.",
        collected_at=collected_at,
    )

    write_raw_documents(path, [document])

    assert '"collected_at": "2026-07-29T13:00:00+00:00"' in path.read_text(encoding="utf-8")


def test_read_raw_documents_rejects_invalid_jsonl_field_type(tmp_path: Path) -> None:
    path = tmp_path / "raw.jsonl"
    path.write_text(
        '{"source_id": "sdis-40", "url": "https://example.com", "canonical_url": null, '
        '"title": null, "content": 123, "published_at": null, "collected_at": null}\n',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="JSONL field must be a string: content"):
        read_raw_documents(path)
