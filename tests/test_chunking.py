from datetime import UTC, datetime

import pytest

from chatbot_incendie.chunking import chunk_document, chunk_documents
from chatbot_incendie.cleaning import clean_and_deduplicate
from chatbot_incendie.connectors import parse_meteo_des_forets_archive
from chatbot_incendie.domain import RawDocument, Source, SourceStatus, SourceType


def test_short_document_returns_one_chunk_with_metadata() -> None:
    document = _document("Short wildfire update.")

    chunks = chunk_document(document, max_chars=80, overlap_chars=10)

    assert len(chunks) == 1
    assert chunks[0].content == "Short wildfire update."
    assert chunks[0].chunk_index == 0
    assert chunks[0].chunk_count == 1
    assert chunks[0].source_id == document.source_id
    assert chunks[0].document_url == document.url
    assert chunks[0].canonical_url == document.canonical_url
    assert chunks[0].title == document.title
    assert chunks[0].published_at == document.published_at
    assert chunks[0].collected_at == document.collected_at


def test_paragraphs_are_packed_when_they_fit() -> None:
    chunks = chunk_document(_document("Alpha.\n\nBeta.\n\nGamma."), max_chars=22, overlap_chars=0)

    assert [chunk.content for chunk in chunks] == ["Alpha.\n\nBeta.\n\nGamma."]


def test_paragraphs_split_when_they_do_not_fit() -> None:
    chunks = chunk_document(
        _document("Alpha beta gamma.\n\nDelta epsilon zeta.\n\nEta theta iota."),
        max_chars=25,
        overlap_chars=0,
    )

    assert [chunk.chunk_index for chunk in chunks] == [0, 1, 2]
    assert [chunk.chunk_count for chunk in chunks] == [3, 3, 3]
    assert [chunk.content for chunk in chunks] == [
        "Alpha beta gamma.",
        "Delta epsilon zeta.",
        "Eta theta iota.",
    ]


def test_long_paragraph_splits_by_words_with_bounds() -> None:
    chunks = chunk_document(
        _document("one two three four five six seven eight"),
        max_chars=18,
        overlap_chars=0,
    )

    assert [chunk.content for chunk in chunks] == [
        "one two three four",
        "five six seven",
        "eight",
    ]
    assert all(len(chunk.content) <= 18 for chunk in chunks)


def test_overlap_is_added_to_adjacent_chunks_within_max_chars() -> None:
    chunks = chunk_document(
        _document("one two three four five six seven eight"),
        max_chars=22,
        overlap_chars=5,
    )

    assert len(chunks) > 1
    assert chunks[1].content.startswith(chunks[0].content[-5:])
    assert all(len(chunk.content) <= 22 for chunk in chunks)


def test_chunk_documents_preserves_document_order_and_resets_indexes() -> None:
    documents = [
        _document("A B C D E F", url="https://example.com/a"),
        _document("G", url="https://example.com/b"),
    ]

    chunks = chunk_documents(documents, max_chars=5, overlap_chars=0)

    assert [chunk.content for chunk in chunks] == ["A B C", "D E F", "G"]
    assert [chunk.chunk_index for chunk in chunks] == [0, 1, 0]
    assert [chunk.chunk_count for chunk in chunks] == [2, 2, 1]


@pytest.mark.parametrize(
    ("max_chars", "overlap_chars"),
    [
        (0, 0),
        (10, -1),
        (10, 10),
    ],
)
def test_invalid_chunk_config_raises(max_chars: int, overlap_chars: int) -> None:
    with pytest.raises(ValueError):
        chunk_document(_document("Content"), max_chars=max_chars, overlap_chars=overlap_chars)


def test_meteo_des_forets_documents_flow_through_cleaning_and_chunking() -> None:
    source = _source()
    documents = parse_meteo_des_forets_archive(
        csv_text=(
            "Reference_time,dep_code,niveau_j1,niveau_j2,nom_dep\n"
            "2026-07-29T17:00:00+00:00,33,3,4,Gironde\n"
            "2026-07-29T17:00:00+00:00,40,4,4,Landes\n"
        ),
        source=source,
        archive_url="https://example.com/mdf.csv",
    )
    cleaned = clean_and_deduplicate(documents)

    chunks = chunk_documents(cleaned.documents, max_chars=800, overlap_chars=120)

    assert cleaned.output_count == 2
    assert len(chunks) == 2
    assert [chunk.title for chunk in chunks] == [
        "Meteo des forets 33 - 2026-07-29T17:00:00+00:00",
        "Meteo des forets 40 - 2026-07-29T17:00:00+00:00",
    ]


def _document(
    content: str,
    *,
    url: str = "https://example.com/doc",
) -> RawDocument:
    return RawDocument(
        source_id="source-a",
        url=url,
        canonical_url="https://example.com/canonical",
        title="Incident update",
        content=content,
        published_at=datetime(2026, 7, 29, 17, 0, tzinfo=UTC),
        collected_at=datetime(2026, 7, 29, 18, 0, tzinfo=UTC),
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
