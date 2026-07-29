from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import pytest

from chatbot_incendie.chunking import chunk_documents
from chatbot_incendie.cleaning import clean_and_deduplicate
from chatbot_incendie.connectors import (
    GeorisquesConnector,
    MeteoDesForetsArchiveConnector,
    MeteoDesForetsRealtimeConnector,
    MeteoFranceVigilanceConnector,
    NasaFirmsAreaConnector,
    parse_meteo_des_forets_archive,
)
from chatbot_incendie.domain import RawDocument, Source, SourceStatus, SourceType
from chatbot_incendie.embeddings import embed_chunks
from chatbot_incendie.ingestion import run_ingestion
from chatbot_incendie.jsonl_store import read_raw_documents


@dataclass(frozen=True)
class FakeTextClient:
    text: str

    def get_text(self, url: str) -> str:
        return self.text


@dataclass
class FakeAuthenticatedTextClient:
    text_by_department: dict[str, str]
    calls: list[tuple[str, dict[str, str]]] = field(default_factory=list)

    def get_text(self, url: str, headers: Mapping[str, str]) -> str:
        self.calls.append((url, dict(headers)))
        department = url.rsplit("id-departement=", maxsplit=1)[1]
        return self.text_by_department[department]


@dataclass
class FakeMappingAuthenticatedTextClient:
    text_by_url: dict[str, str]
    calls: list[tuple[str, dict[str, str]]] = field(default_factory=list)

    def get_text(self, url: str, headers: Mapping[str, str]) -> str:
        self.calls.append((url, dict(headers)))
        return self.text_by_url[url]


@dataclass(frozen=True)
class FakePartlyFailingAuthenticatedTextClient:
    text_by_url: dict[str, str]

    def get_text(self, url: str, headers: Mapping[str, str]) -> str:
        if url not in self.text_by_url:
            raise OSError("network failed")
        return self.text_by_url[url]


@dataclass(frozen=True)
class DocumentsCollector:
    documents: list[RawDocument]

    def fetch(self) -> list[RawDocument]:
        return self.documents


class FakeEmbeddingModel:
    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        return [[float(len(text)), 1.0] for text in texts]


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


def test_meteo_des_forets_parser_accepts_realtime_csv_field_names() -> None:
    csv_text = (
        "reference_time;dep_code;niveau_j1;niveau_j2;dep_nom\n2026-07-28T14:50:04Z;33;3;2;Gironde\n"
    )

    documents = parse_meteo_des_forets_archive(csv_text, _source(), "https://example.com/mdf.csv")

    assert documents[0].title == "Meteo des forets 33 - 2026-07-28T14:50:04Z"
    assert "Departement 33 (Gironde)" in documents[0].content


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


def test_meteo_des_forets_realtime_connector_requests_departments_with_api_key() -> None:
    source = _realtime_source()
    client = FakeAuthenticatedTextClient(
        {
            "33": _csv_for_department("33", "Gironde"),
            "40": _csv_for_department("40", "Landes"),
        }
    )
    connector = MeteoDesForetsRealtimeConnector(
        client=client,
        api_key="test-key",
        base_url="https://example.com/api",
    )

    documents = connector.fetch(source)

    assert [document.title for document in documents] == [
        "Meteo des forets 33 - 2026-07-29T17:00:00+00:00",
        "Meteo des forets 40 - 2026-07-29T17:00:00+00:00",
    ]
    assert [headers for _, headers in client.calls] == [
        {"apikey": "test-key"},
        {"apikey": "test-key"},
    ]
    assert [
        url.removeprefix("https://example.com/api/carte/departement/encours?")
        for url, _ in client.calls
    ] == [
        "format=csv&echeance=J1J2&id-departement=33",
        "format=csv&echeance=J1J2&id-departement=40",
    ]


def test_meteo_des_forets_realtime_connector_rejects_empty_api_key() -> None:
    connector = MeteoDesForetsRealtimeConnector(
        client=FakeAuthenticatedTextClient({"33": _csv_for_department("33", "Gironde")}),
        api_key=" ",
    )

    with pytest.raises(ValueError, match="API key must not be empty"):
        connector.fetch(_realtime_source())


def test_nasa_firms_area_connector_parses_hotspot_csv() -> None:
    source = _source_with_id("nasa-firms-area-api")
    url = "https://example.com/firms/test-key/VIIRS_SNPP_NRT/-1.6,43.45,0.0,45.7/1"
    connector = NasaFirmsAreaConnector(
        client=FakeMappingAuthenticatedTextClient({url: _nasa_csv()}),
        map_key="test-key",
        base_url="https://example.com/firms",
    )

    documents = connector.fetch(source)

    assert len(documents) == 1
    assert documents[0].source_id == "nasa-firms-area-api"
    assert documents[0].title == "NASA FIRMS hotspot 2026-07-29 1435 (44.65, -1.15)"
    assert "FRP: 12.4" in documents[0].content
    assert documents[0].published_at == datetime(2026, 7, 29, 14, 35, tzinfo=UTC)


def test_nasa_firms_area_connector_returns_empty_list_for_header_only_csv() -> None:
    source = _source_with_id("nasa-firms-area-api")
    url = "https://example.com/firms/test-key/VIIRS_SNPP_NRT/-1.6,43.45,0.0,45.7/1"
    connector = NasaFirmsAreaConnector(
        client=FakeMappingAuthenticatedTextClient(
            {url: "latitude,longitude,acq_date,acq_time,frp\n"}
        ),
        map_key="test-key",
        base_url="https://example.com/firms",
    )

    assert connector.fetch(source) == []


def test_nasa_firms_area_connector_rejects_malformed_csv() -> None:
    source = _source_with_id("nasa-firms-area-api")
    url = "https://example.com/firms/test-key/VIIRS_SNPP_NRT/-1.6,43.45,0.0,45.7/1"
    connector = NasaFirmsAreaConnector(
        client=FakeMappingAuthenticatedTextClient({url: "latitude,longitude,acq_date\n"}),
        map_key="test-key",
        base_url="https://example.com/firms",
    )

    with pytest.raises(ValueError, match="NASA FIRMS CSV is missing required fields: acq_time"):
        connector.fetch(source)


def test_meteo_france_vigilance_connector_parses_current_bulletin() -> None:
    source = _source_with_id("meteo-france-vigilance-api")
    url = "https://example.com/vigilance/cartevigilance/encours"
    connector = MeteoFranceVigilanceConnector(
        client=FakeMappingAuthenticatedTextClient({url: _vigilance_json()}),
        api_key="test-key",
        base_url="https://example.com/vigilance",
    )

    documents = connector.fetch(source)

    assert len(documents) == 1
    assert documents[0].title == "Meteo-France vigilance Gironde Landes"
    assert "Gironde et Landes" in documents[0].content
    assert documents[0].published_at == datetime(2026, 7, 29, 14, 1, 5, tzinfo=UTC)


def test_meteo_france_vigilance_connector_returns_empty_list_for_empty_json() -> None:
    source = _source_with_id("meteo-france-vigilance-api")
    url = "https://example.com/vigilance/cartevigilance/encours"
    connector = MeteoFranceVigilanceConnector(
        client=FakeMappingAuthenticatedTextClient({url: "{}"}),
        api_key="test-key",
        base_url="https://example.com/vigilance",
    )

    assert connector.fetch(source) == []


def test_meteo_france_vigilance_connector_rejects_malformed_json() -> None:
    source = _source_with_id("meteo-france-vigilance-api")
    url = "https://example.com/vigilance/cartevigilance/encours"
    connector = MeteoFranceVigilanceConnector(
        client=FakeMappingAuthenticatedTextClient({url: "["}),
        api_key="test-key",
        base_url="https://example.com/vigilance",
    )

    with pytest.raises(ValueError, match="Meteo-France Vigilance response must be valid JSON"):
        connector.fetch(source)


def test_georisques_connector_parses_commune_report() -> None:
    source = _source_with_id("georisques-api")
    url = "https://example.com/georisques/resultats_rapport_risque?code_insee=33051"
    connector = GeorisquesConnector(
        client=FakeMappingAuthenticatedTextClient({url: _georisques_json()}),
        base_url="https://example.com/georisques",
        commune_codes=("33051",),
    )

    documents = connector.fetch(source)

    assert len(documents) == 1
    assert documents[0].title == "Georisques BIGANOS (33051)"
    assert documents[0].canonical_url == "https://www.georisques.gouv.fr/mes-risques/33051"
    assert "risquesNaturels: Feu de foret" in documents[0].content


def test_georisques_connector_returns_empty_list_for_empty_json() -> None:
    source = _source_with_id("georisques-api")
    url = "https://example.com/georisques/resultats_rapport_risque?code_insee=33051"
    connector = GeorisquesConnector(
        client=FakeMappingAuthenticatedTextClient({url: "{}"}),
        base_url="https://example.com/georisques",
        commune_codes=("33051",),
    )

    assert connector.fetch(source) == []


def test_georisques_connector_rejects_malformed_report() -> None:
    source = _source_with_id("georisques-api")
    url = "https://example.com/georisques/resultats_rapport_risque?code_insee=33051"
    connector = GeorisquesConnector(
        client=FakeMappingAuthenticatedTextClient({url: '{"commune": {}}'}),
        base_url="https://example.com/georisques",
        commune_codes=("33051",),
    )

    with pytest.raises(ValueError, match="Georisques commune field must not be empty: libelle"):
        connector.fetch(source)


def test_georisques_connector_skips_commune_network_failures() -> None:
    source = _source_with_id("georisques-api")
    url = "https://example.com/georisques/resultats_rapport_risque?code_insee=33051"
    connector = GeorisquesConnector(
        client=FakePartlyFailingAuthenticatedTextClient({url: _georisques_json()}),
        base_url="https://example.com/georisques",
        commune_codes=("33051", "33529"),
    )

    documents = connector.fetch(source)

    assert [document.title for document in documents] == ["Georisques BIGANOS (33051)"]


def test_new_connectors_flow_through_cleaning_chunking_and_fake_embeddings() -> None:
    documents = [
        *_nasa_connector().fetch(_source_with_id("nasa-firms-area-api")),
        *_vigilance_connector().fetch(_source_with_id("meteo-france-vigilance-api")),
        *_georisques_connector().fetch(_source_with_id("georisques-api")),
    ]

    cleaned = clean_and_deduplicate(documents)
    chunks = chunk_documents(cleaned.documents, max_chars=300, overlap_chars=30)
    embedded = embed_chunks(chunks, FakeEmbeddingModel())

    assert cleaned.output_count == 3
    assert len(embedded) >= 3
    assert {chunk.source_id for chunk in embedded} == {
        "nasa-firms-area-api",
        "meteo-france-vigilance-api",
        "georisques-api",
    }


def _csv() -> str:
    return (
        "Reference_time,dep_code,niveau_j1,niveau_j2,nom_dep\n"
        "2026-07-29T17:00:00+00:00,33,3,4,Gironde\n"
        "2026-07-29T17:00:00+00:00,40,4,4,Landes\n"
        "2026-07-29T17:00:00+00:00,24,2,3,Dordogne\n"
    )


def _nasa_csv() -> str:
    return (
        "latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,satellite,"
        "instrument,confidence,version,bright_ti5,frp,daynight\n"
        "44.65,-1.15,310.2,0.5,0.5,2026-07-29,1435,N,VIIRS,n,2.0NRT,290.1,12.4,D\n"
    )


def _vigilance_json() -> str:
    return (
        '{"product":{"update_time":"2026-07-29T14:01:05Z",'
        '"text_items":{"title":"Commentaire carte",'
        '"text":["Pic de chaleur en Gironde et Landes."]},'
        '"33":{"color_id":3},"40":{"color_id":3}}}'
    )


def _georisques_json() -> str:
    return (
        '{"commune":{"libelle":"BIGANOS","codeInsee":"33051"},'
        '"url":"https://www.georisques.gouv.fr/mes-risques/33051",'
        '"risquesNaturels":{"feuForet":{"present":true,"libelle":"Feu de foret"},'
        '"inondation":{"present":false,"libelle":"Inondation"}}}'
    )


def _nasa_connector() -> NasaFirmsAreaConnector:
    url = "https://example.com/firms/test-key/VIIRS_SNPP_NRT/-1.6,43.45,0.0,45.7/1"
    return NasaFirmsAreaConnector(
        client=FakeMappingAuthenticatedTextClient({url: _nasa_csv()}),
        map_key="test-key",
        base_url="https://example.com/firms",
    )


def _vigilance_connector() -> MeteoFranceVigilanceConnector:
    url = "https://example.com/vigilance/cartevigilance/encours"
    return MeteoFranceVigilanceConnector(
        client=FakeMappingAuthenticatedTextClient({url: _vigilance_json()}),
        api_key="test-key",
        base_url="https://example.com/vigilance",
    )


def _georisques_connector() -> GeorisquesConnector:
    url = "https://example.com/georisques/resultats_rapport_risque?code_insee=33051"
    return GeorisquesConnector(
        client=FakeMappingAuthenticatedTextClient({url: _georisques_json()}),
        base_url="https://example.com/georisques",
        commune_codes=("33051",),
    )


def _csv_for_department(dep_code: str, dep_name: str) -> str:
    return (
        "Reference_time,dep_code,niveau_j1,niveau_j2,nom_dep\n"
        f"2026-07-29T17:00:00+00:00,{dep_code},3,4,{dep_name}\n"
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


def _realtime_source() -> Source:
    return Source(
        id="meteo-des-forets-realtime",
        name="Meteo des forets realtime",
        type=SourceType.API,
        url="https://public-api.meteofrance.fr/public/DPMeteoForets/v1",
        status=SourceStatus.CANDIDATE,
        usage_notes="Real-time wildfire danger prevention context.",
        rate_limit_notes="Portal quota to verify.",
    )


def _source_with_id(source_id: str) -> Source:
    return Source(
        id=source_id,
        name=source_id,
        type=SourceType.API,
        url="https://example.com/source",
        status=SourceStatus.CANDIDATE,
        usage_notes="Test source.",
        rate_limit_notes="Test rate limits.",
    )
