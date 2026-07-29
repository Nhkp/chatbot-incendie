from datetime import UTC, datetime

import pytest

from chatbot_incendie.domain import RawDocument, Source, SourceStatus, SourceType


def test_source_accepts_valid_values() -> None:
    source = Source(
        id="gironde-prefecture",
        name="Gironde Prefecture",
        type=SourceType.OFFICIAL_WEBSITE,
        url="https://www.gironde.gouv.fr/",
        status=SourceStatus.CANDIDATE,
        usage_notes="Official local information.",
        rate_limit_notes="Conservative polling.",
    )

    assert source.id == "gironde-prefecture"


def test_source_rejects_invalid_url() -> None:
    with pytest.raises(ValueError, match="url must be HTTP"):
        Source(
            id="bad",
            name="Bad",
            type=SourceType.NEWS,
            url="ftp://example.com",
            status=SourceStatus.CANDIDATE,
            usage_notes="Usage notes.",
            rate_limit_notes="Rate-limit notes.",
        )


def test_source_rejects_unknown_type() -> None:
    with pytest.raises(ValueError):
        SourceType("blog")


def test_source_rejects_unknown_status() -> None:
    with pytest.raises(ValueError):
        SourceStatus("validated")


def test_raw_document_rejects_empty_content() -> None:
    with pytest.raises(ValueError, match="document content must not be empty"):
        RawDocument(source_id="sdis-33", url="https://example.com/doc", content=" ")


def test_raw_document_accepts_metadata() -> None:
    collected_at = datetime(2026, 7, 29, tzinfo=UTC)
    document = RawDocument(
        source_id="sdis-33",
        url="https://example.com/doc",
        canonical_url="https://example.com/doc",
        title="Situation update",
        content="A sourced update.",
        collected_at=collected_at,
    )

    assert document.collected_at == collected_at
