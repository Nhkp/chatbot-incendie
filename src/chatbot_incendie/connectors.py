from __future__ import annotations

import csv
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from io import StringIO
from typing import Protocol, cast
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from chatbot_incendie.domain import RawDocument, Source

TARGET_DEPARTMENTS = {"33", "40"}
METEO_DES_FORETS_API_BASE_URL = "https://public-api.meteofrance.fr/public/DPMeteoForets/v1"
METEO_FRANCE_API_KEY_HEADER = "apikey"
REQUIRED_METEO_DES_FORETS_FIELDS = {
    "Reference_time",
    "dep_code",
    "niveau_j1",
    "niveau_j2",
    "nom_dep",
}
DANGER_LABELS = {
    "1": "faible",
    "2": "modere",
    "3": "eleve",
    "4": "tres eleve",
}


class HttpClient(Protocol):
    def get_text(self, url: str) -> str: ...


class AuthenticatedHttpClient(Protocol):
    def get_text(self, url: str, headers: Mapping[str, str]) -> str: ...


class SourceConnector(Protocol):
    def fetch(self, source: Source) -> list[RawDocument]: ...


@dataclass(frozen=True)
class UrlopenTextClient:
    timeout_seconds: float = 30.0

    def get_text(self, url: str, headers: Mapping[str, str]) -> str:
        request = Request(url=url, headers=dict(headers))
        with urlopen(request, timeout=self.timeout_seconds) as response:
            charset = str(response.headers.get_content_charset() or "utf-8")
            body = cast(bytes, response.read())
            return body.decode(charset)


@dataclass(frozen=True)
class MeteoDesForetsArchiveConnector:
    client: HttpClient
    archive_url: str

    def fetch(self, source: Source) -> list[RawDocument]:
        return parse_meteo_des_forets_archive(
            csv_text=self.client.get_text(self.archive_url),
            source=source,
            archive_url=self.archive_url,
        )


@dataclass(frozen=True)
class MeteoDesForetsRealtimeConnector:
    client: AuthenticatedHttpClient
    api_key: str
    base_url: str = METEO_DES_FORETS_API_BASE_URL
    departments: Sequence[str] = ("33", "40")

    def fetch(self, source: Source) -> list[RawDocument]:
        if not self.api_key.strip():
            raise ValueError("Meteo-France API key must not be empty")

        documents: list[RawDocument] = []
        for department in self.departments:
            url = _realtime_department_url(self.base_url, department)
            documents.extend(
                parse_meteo_des_forets_archive(
                    csv_text=self.client.get_text(
                        url, headers={METEO_FRANCE_API_KEY_HEADER: self.api_key}
                    ),
                    source=source,
                    archive_url=url,
                )
            )
        return documents


def parse_meteo_des_forets_archive(
    csv_text: str,
    source: Source,
    archive_url: str,
) -> list[RawDocument]:
    reader = csv.DictReader(StringIO(csv_text), delimiter=_detect_delimiter(csv_text))
    if reader.fieldnames is None:
        raise ValueError("Meteo des forets CSV must contain a header")

    missing_fields = REQUIRED_METEO_DES_FORETS_FIELDS - set(reader.fieldnames)
    if missing_fields:
        missing = ", ".join(sorted(missing_fields))
        raise ValueError(f"Meteo des forets CSV is missing required fields: {missing}")

    documents: list[RawDocument] = []
    for row in reader:
        dep_code = _required_field(row, "dep_code")
        if dep_code not in TARGET_DEPARTMENTS:
            continue
        documents.append(
            RawDocument(
                source_id=source.id,
                url=archive_url,
                canonical_url=f"{archive_url}#{_required_field(row, 'Reference_time')}-{dep_code}",
                title=f"Meteo des forets {dep_code} - {_required_field(row, 'Reference_time')}",
                content=_content_from_row(row),
                published_at=_parse_reference_time(_required_field(row, "Reference_time")),
            )
        )
    return documents


def _detect_delimiter(csv_text: str) -> str:
    header = csv_text.splitlines()[0] if csv_text.splitlines() else ""
    return ";" if header.count(";") > header.count(",") else ","


def _realtime_department_url(base_url: str, department: str) -> str:
    query = urlencode({"format": "csv", "echeance": "J1J2", "id-departement": department})
    return f"{base_url.rstrip('/')}/carte/departement/encours?{query}"


def _content_from_row(row: dict[str, str | None]) -> str:
    dep_code = _required_field(row, "dep_code")
    dep_name = _required_field(row, "nom_dep")
    niveau_j1 = _danger_level(row, "niveau_j1")
    niveau_j2 = _danger_level(row, "niveau_j2")
    reference_time = _required_field(row, "Reference_time")
    return (
        "Meteo des forets, source Meteo-France. "
        f"Departement {dep_code} ({dep_name}). "
        f"Reference: {reference_time}. "
        f"Danger feu de foret J+1: niveau {niveau_j1} ({DANGER_LABELS[niveau_j1]}). "
        f"Danger feu de foret J+2: niveau {niveau_j2} ({DANGER_LABELS[niveau_j2]}). "
        "Cette donnee de prevention n'est pas une carte des incendies en cours."
    )


def _required_field(row: dict[str, str | None], field: str) -> str:
    value = row[field]
    if value is None or not value.strip():
        raise ValueError(f"Meteo des forets CSV field must not be empty: {field}")
    return value.strip()


def _danger_level(row: dict[str, str | None], field: str) -> str:
    value = _required_field(row, field)
    if value not in DANGER_LABELS:
        raise ValueError(f"Meteo des forets danger level must be 1, 2, 3, or 4: {field}")
    return value


def _parse_reference_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
