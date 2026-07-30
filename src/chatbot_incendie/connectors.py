from __future__ import annotations

import csv
import json
import re
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from html import unescape
from http.client import RemoteDisconnected
from io import StringIO
from typing import Any, Protocol, cast
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from chatbot_incendie.domain import RawDocument, Source

TARGET_DEPARTMENTS = {"33", "40"}
METEO_DES_FORETS_API_BASE_URL = "https://public-api.meteofrance.fr/public/DPMeteoForets/v1"
METEO_FRANCE_VIGILANCE_API_BASE_URL = "https://public-api.meteofrance.fr/public/DPVigilance/v1"
METEO_FRANCE_API_KEY_HEADER = "apikey"
NASA_FIRMS_AREA_API_BASE_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"
GEORISQUES_API_BASE_URL = "https://www.georisques.gouv.fr/api/v1"
GIRONDE_LANDES_BBOX = (-1.6, 43.45, 0.0, 45.7)
GEORISQUES_COMMUNE_CODES = ("33051", "33529", "33243", "40192", "40279")
METEO_DES_FORETS_FIELD_ALIASES = {
    "Reference_time": ("Reference_time", "reference_time"),
    "dep_code": ("dep_code",),
    "niveau_j1": ("niveau_j1",),
    "niveau_j2": ("niveau_j2",),
    "nom_dep": ("nom_dep", "dep_nom"),
}
DANGER_LABELS = {
    "1": "faible",
    "2": "modere",
    "3": "eleve",
    "4": "tres eleve",
}
NASA_FIRMS_REQUIRED_FIELDS = {"latitude", "longitude", "acq_date", "acq_time"}
MEDIA_RELEVANCE_KEYWORDS = (
    "gironde",
    "landes",
    "incendie",
    "incendies",
    "feu",
    "feux",
    "forêt",
    "foret",
    "évacuation",
    "evacuation",
    "évacué",
    "evacue",
    "pompier",
    "pompiers",
    "sécheresse",
    "secheresse",
    "fumée",
    "fumee",
    "canicule",
    "lacanau",
    "arcachon",
    "andernos",
    "audenge",
    "biganos",
    "mios",
    "sanguinet",
)


class HttpClient(Protocol):
    def get_text(self, url: str) -> str: ...


class AuthenticatedHttpClient(Protocol):
    def get_text(self, url: str, headers: Mapping[str, str]) -> str: ...


class SourceConnector(Protocol):
    def fetch(self, source: Source) -> list[RawDocument]: ...


@dataclass(frozen=True)
class UrlopenTextClient:
    timeout_seconds: float = 30.0
    curl_fallback: bool = True

    def get_text(self, url: str, headers: Mapping[str, str]) -> str:
        request = Request(url=url, headers=dict(headers))
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                charset = str(response.headers.get_content_charset() or "utf-8")
                body = cast(bytes, response.read())
                return body.decode(charset)
        except (RemoteDisconnected, TimeoutError, URLError):
            if not self.curl_fallback:
                raise
            return _curl_get_text(url, headers, self.timeout_seconds)


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


@dataclass(frozen=True)
class NasaFirmsAreaConnector:
    client: AuthenticatedHttpClient
    map_key: str
    base_url: str = NASA_FIRMS_AREA_API_BASE_URL
    source_name: str = "VIIRS_SNPP_NRT"
    bbox: tuple[float, float, float, float] = GIRONDE_LANDES_BBOX
    day_range: int = 1

    def fetch(self, source: Source) -> list[RawDocument]:
        if not self.map_key.strip():
            raise ValueError("NASA FIRMS map key must not be empty")
        url = _nasa_firms_area_url(
            base_url=self.base_url,
            map_key=self.map_key,
            source_name=self.source_name,
            bbox=self.bbox,
            day_range=self.day_range,
        )
        return parse_nasa_firms_area_csv(
            csv_text=self.client.get_text(url, headers=_json_headers()),
            source=source,
            api_url=url,
        )


@dataclass(frozen=True)
class MeteoFranceVigilanceConnector:
    client: AuthenticatedHttpClient
    api_key: str
    base_url: str = METEO_FRANCE_VIGILANCE_API_BASE_URL

    def fetch(self, source: Source) -> list[RawDocument]:
        if not self.api_key.strip():
            raise ValueError("Meteo-France API key must not be empty")
        url = f"{self.base_url.rstrip('/')}/cartevigilance/encours"
        return parse_meteo_france_vigilance(
            json_text=self.client.get_text(
                url,
                headers={METEO_FRANCE_API_KEY_HEADER: self.api_key},
            ),
            source=source,
            api_url=url,
        )


@dataclass(frozen=True)
class GeorisquesConnector:
    client: AuthenticatedHttpClient
    base_url: str = GEORISQUES_API_BASE_URL
    commune_codes: Sequence[str] = GEORISQUES_COMMUNE_CODES

    def fetch(self, source: Source) -> list[RawDocument]:
        documents: list[RawDocument] = []
        for commune_code in self.commune_codes:
            url = _georisques_commune_url(self.base_url, commune_code)
            try:
                documents.extend(
                    parse_georisques_report(
                        json_text=self.client.get_text(url, headers=_georisques_headers()),
                        source=source,
                        api_url=url,
                    )
                )
            except (OSError, RemoteDisconnected, URLError, subprocess.CalledProcessError):
                continue
        return documents


@dataclass(frozen=True)
class MediaFeedConnector:
    client: AuthenticatedHttpClient
    feed_url: str
    keywords: Sequence[str] = MEDIA_RELEVANCE_KEYWORDS

    def fetch(self, source: Source) -> list[RawDocument]:
        return parse_media_feed(
            xml_text=self.client.get_text(self.feed_url, headers=_xml_headers()),
            source=source,
            feed_url=self.feed_url,
            keywords=self.keywords,
        )


def parse_meteo_des_forets_archive(
    csv_text: str,
    source: Source,
    archive_url: str,
) -> list[RawDocument]:
    reader = csv.DictReader(StringIO(csv_text), delimiter=_detect_delimiter(csv_text))
    if reader.fieldnames is None:
        raise ValueError("Meteo des forets CSV must contain a header")

    fieldnames = set(reader.fieldnames)
    missing_fields = {
        field
        for field, aliases in METEO_DES_FORETS_FIELD_ALIASES.items()
        if fieldnames.isdisjoint(aliases)
    }
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


def parse_nasa_firms_area_csv(
    csv_text: str,
    source: Source,
    api_url: str,
) -> list[RawDocument]:
    reader = csv.DictReader(StringIO(csv_text), delimiter=_detect_delimiter(csv_text))
    if reader.fieldnames is None:
        raise ValueError("NASA FIRMS CSV must contain a header")

    missing_fields = NASA_FIRMS_REQUIRED_FIELDS - set(reader.fieldnames)
    if missing_fields:
        missing = ", ".join(sorted(missing_fields))
        raise ValueError(f"NASA FIRMS CSV is missing required fields: {missing}")

    documents: list[RawDocument] = []
    for row in reader:
        latitude = _required_csv_value(row, "latitude", "NASA FIRMS")
        longitude = _required_csv_value(row, "longitude", "NASA FIRMS")
        acq_date = _required_csv_value(row, "acq_date", "NASA FIRMS")
        acq_time = _required_csv_value(row, "acq_time", "NASA FIRMS").zfill(4)
        fingerprint = f"{latitude}-{longitude}-{acq_date}-{acq_time}"
        documents.append(
            RawDocument(
                source_id=source.id,
                url=api_url,
                canonical_url=f"{api_url}#{fingerprint}",
                title=f"NASA FIRMS hotspot {acq_date} {acq_time} ({latitude}, {longitude})",
                content=_nasa_firms_content(row, latitude, longitude, acq_date, acq_time),
                published_at=_parse_nasa_acquisition_time(acq_date, acq_time),
            )
        )
    return documents


def parse_meteo_france_vigilance(
    json_text: str,
    source: Source,
    api_url: str,
) -> list[RawDocument]:
    data = _json_object(json_text, "Meteo-France Vigilance")
    if not data:
        return []

    product = _as_mapping(data.get("product", data), "Meteo-France Vigilance product")
    update_time = _optional_text(product.get("update_time"))
    text_items = _vigilance_text_items(product)
    department_mentions = sorted(_department_mentions(product))
    if not update_time and not text_items and not department_mentions:
        return []

    return [
        RawDocument(
            source_id=source.id,
            url=api_url,
            canonical_url=f"{api_url}#{update_time or 'latest'}",
            title="Meteo-France vigilance Gironde Landes",
            content=_vigilance_content(
                update_time=update_time,
                text_items=text_items,
                department_mentions=department_mentions,
            ),
            published_at=_parse_optional_datetime(update_time),
        )
    ]


def parse_georisques_report(
    json_text: str,
    source: Source,
    api_url: str,
) -> list[RawDocument]:
    data = _json_object(json_text, "Georisques")
    if not data:
        return []

    commune = _as_mapping(data.get("commune"), "Georisques commune")
    commune_name = _required_mapping_text(commune, "libelle", "Georisques commune")
    commune_code = _required_mapping_text(commune, "codeInsee", "Georisques commune")
    return [
        RawDocument(
            source_id=source.id,
            url=api_url,
            canonical_url=_http_url_or_none(_optional_text(data.get("url"))) or api_url,
            title=f"Georisques {commune_name} ({commune_code})",
            content=_georisques_content(data, commune_name, commune_code),
        )
    ]


def parse_media_feed(
    xml_text: str,
    source: Source,
    feed_url: str,
    keywords: Sequence[str] = MEDIA_RELEVANCE_KEYWORDS,
) -> list[RawDocument]:
    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError as error:
        raise ValueError("media feed response must be valid XML") from error

    documents: list[RawDocument] = []
    for entry in _media_feed_entries(root):
        document = _media_document_from_entry(source, feed_url, entry)
        if document is not None and _is_relevant_media_document(document, keywords):
            documents.append(document)
    return documents


def _detect_delimiter(csv_text: str) -> str:
    header = csv_text.splitlines()[0] if csv_text.splitlines() else ""
    return ";" if header.count(";") > header.count(",") else ","


def _realtime_department_url(base_url: str, department: str) -> str:
    query = urlencode({"format": "csv", "echeance": "J1J2", "id-departement": department})
    return f"{base_url.rstrip('/')}/carte/departement/encours?{query}"


def _nasa_firms_area_url(
    *,
    base_url: str,
    map_key: str,
    source_name: str,
    bbox: tuple[float, float, float, float],
    day_range: int,
) -> str:
    bbox_text = ",".join(str(value) for value in bbox)
    return f"{base_url.rstrip('/')}/{map_key}/{source_name}/{bbox_text}/{day_range}"


def _georisques_commune_url(base_url: str, commune_code: str) -> str:
    query = urlencode({"code_insee": commune_code})
    return f"{base_url.rstrip('/')}/resultats_rapport_risque?{query}"


def _json_headers() -> dict[str, str]:
    return {
        "Accept": "application/json,text/csv;q=0.9,*/*;q=0.8",
        "Connection": "close",
        "User-Agent": "chatbot-incendie/0.1",
    }


def _xml_headers() -> dict[str, str]:
    return {
        "Accept": "application/rss+xml,application/atom+xml,application/xml,text/xml,*/*;q=0.8",
        "User-Agent": "chatbot-incendie/0.1",
    }


def _georisques_headers() -> dict[str, str]:
    return {
        "Accept": "application/json",
        "User-Agent": "chatbot-incendie/0.1",
    }


def _curl_get_text(url: str, headers: Mapping[str, str], timeout_seconds: float) -> str:
    command = [
        "curl",
        "--http1.1",
        "--fail",
        "--location",
        "--silent",
        "--show-error",
        "--max-time",
        str(timeout_seconds),
    ]
    for key, value in headers.items():
        command.extend(["--header", f"{key}: {value}"])
    command.append(url)
    # ponytail: curl is a pragmatic fallback for APIs that close urllib connections;
    # replace with a real HTTP dependency if connector-specific HTTP behavior grows.
    completed = subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
        timeout=timeout_seconds + 5,
    )
    return completed.stdout


def _media_feed_entries(root: ElementTree.Element) -> list[ElementTree.Element]:
    entry_names = {"item", "entry", "url"}
    if _xml_name(root.tag) in entry_names:
        return [root]
    return [element for element in root.iter() if _xml_name(element.tag) in entry_names]


def _media_document_from_entry(
    source: Source,
    feed_url: str,
    entry: ElementTree.Element,
) -> RawDocument | None:
    title = _entry_title(entry)
    link = _entry_link(entry)
    if title is None or link is None:
        return None

    summary = _entry_summary(entry)
    published_at = _entry_published_at(entry)
    content_parts = [
        f"Media source: {source.name}.",
        f"Title: {title}.",
    ]
    if summary:
        content_parts.append(f"Summary: {summary}.")
    content_parts.append(
        "Media context is not an official emergency instruction; "
        "confirm safety actions with official sources."
    )
    return RawDocument(
        source_id=source.id,
        url=feed_url,
        canonical_url=link,
        title=title,
        content=" ".join(content_parts),
        published_at=published_at,
    )


def _entry_title(entry: ElementTree.Element) -> str | None:
    return _clean_feed_text(_child_text(entry, "title") or _child_text(entry, "news:title"))


def _entry_link(entry: ElementTree.Element) -> str | None:
    link = _child_text(entry, "link") or _child_text(entry, "loc")
    if link:
        return _http_url_or_none(_clean_feed_text(link))
    for child in entry:
        if _xml_name(child.tag) == "link":
            href = child.attrib.get("href")
            if href:
                return _http_url_or_none(_clean_feed_text(href))
    return None


def _entry_summary(entry: ElementTree.Element) -> str | None:
    texts = [
        _child_text(entry, "description"),
        _child_text(entry, "summary"),
        _child_text(entry, "content"),
        _child_text(entry, "news:keywords"),
        _child_text(entry, "image:caption"),
    ]
    return _clean_feed_text(" ".join(text for text in texts if text))


def _entry_published_at(entry: ElementTree.Element) -> datetime | None:
    value = _clean_feed_text(
        _child_text(entry, "pubDate")
        or _child_text(entry, "published")
        or _child_text(entry, "updated")
        or _child_text(entry, "lastmod")
        or _child_text(entry, "news:publication_date")
    )
    if value is None:
        return None
    try:
        return _parse_optional_datetime(value) or _parse_rfc2822_datetime(value)
    except ValueError:
        return _parse_rfc2822_datetime(value)


def _parse_rfc2822_datetime(value: str) -> datetime | None:
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def _child_text(entry: ElementTree.Element, name: str) -> str | None:
    target = name.rsplit(":", maxsplit=1)[-1]
    for child in entry.iter():
        if child is not entry and _xml_name(child.tag) == target and child.text:
            return child.text
    return None


def _xml_name(tag: str) -> str:
    return tag.rsplit("}", maxsplit=1)[-1]


def _clean_feed_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = re.sub(r"<[^>]+>", " ", unescape(value))
    normalized = re.sub(r"\s+", " ", text).strip()
    return normalized or None


def _is_relevant_media_document(document: RawDocument, keywords: Sequence[str]) -> bool:
    content_without_source = re.sub(r"^Media source: .*?\. ", "", document.content)
    haystack = " ".join(
        part for part in (document.title, content_without_source) if part
    ).casefold()
    return any(keyword.casefold() in haystack for keyword in keywords)


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
    for alias in METEO_DES_FORETS_FIELD_ALIASES[field]:
        value = row.get(alias)
        if value is not None and value.strip():
            return value.strip()
    raise ValueError(f"Meteo des forets CSV field must not be empty: {field}")


def _required_csv_value(row: dict[str, str | None], field: str, source_name: str) -> str:
    value = row.get(field)
    if value is not None and value.strip():
        return value.strip()
    raise ValueError(f"{source_name} CSV field must not be empty: {field}")


def _danger_level(row: dict[str, str | None], field: str) -> str:
    value = _required_field(row, field)
    if value not in DANGER_LABELS:
        raise ValueError(f"Meteo des forets danger level must be 1, 2, 3, or 4: {field}")
    return value


def _parse_reference_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _parse_nasa_acquisition_time(acq_date: str, acq_time: str) -> datetime:
    return datetime.strptime(f"{acq_date} {acq_time}", "%Y-%m-%d %H%M").replace(tzinfo=UTC)


def _parse_optional_datetime(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None


def _nasa_firms_content(
    row: dict[str, str | None],
    latitude: str,
    longitude: str,
    acq_date: str,
    acq_time: str,
) -> str:
    optional_parts = [
        ("Satellite", row.get("satellite")),
        ("Instrument", row.get("instrument")),
        ("Confidence", row.get("confidence")),
        ("FRP", row.get("frp")),
        ("Day/night", row.get("daynight")),
    ]
    details = " ".join(
        f"{label}: {value.strip()}." for label, value in optional_parts if value and value.strip()
    )
    return (
        "NASA FIRMS active fire or hotspot detection. "
        f"Location: latitude {latitude}, longitude {longitude}. "
        f"Acquisition: {acq_date} {acq_time} UTC. "
        f"{details} "
        "Satellite hotspots are detection context, not evacuation instructions."
    ).strip()


def _json_object(json_text: str, source_name: str) -> dict[str, Any]:
    try:
        data = json.loads(json_text)
    except json.JSONDecodeError as error:
        raise ValueError(f"{source_name} response must be valid JSON") from error
    if not isinstance(data, dict):
        raise ValueError(f"{source_name} response must be a JSON object")
    return data


def _as_mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return cast(dict[str, Any], value)


def _optional_text(value: object) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _required_mapping_text(data: Mapping[str, object], field: str, label: str) -> str:
    value = _optional_text(data.get(field))
    if value is None:
        raise ValueError(f"{label} field must not be empty: {field}")
    return value


def _http_url_or_none(value: str | None) -> str | None:
    return value if value and value.startswith(("http://", "https://")) else None


def _vigilance_text_items(product: Mapping[str, object]) -> list[str]:
    items: list[str] = []
    for value in _walk_json(product):
        if isinstance(value, str) and ("Gironde" in value or "Landes" in value):
            items.append(value.strip())
        elif isinstance(value, list) and all(isinstance(item, str) for item in value):
            text = " ".join(item.strip() for item in value if item.strip())
            if "Gironde" in text or "Landes" in text:
                items.append(text)
    return _unique_texts(items)


def _department_mentions(value: object) -> set[str]:
    mentions: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            if str(item) in TARGET_DEPARTMENTS:
                mentions.add(str(item))
            if str(key) in TARGET_DEPARTMENTS:
                mentions.add(str(key))
            mentions.update(_department_mentions(item))
    elif isinstance(value, list):
        for item in value:
            mentions.update(_department_mentions(item))
    return mentions & TARGET_DEPARTMENTS


def _walk_json(value: object) -> list[object]:
    values = [value]
    if isinstance(value, dict):
        for item in value.values():
            values.extend(_walk_json(item))
    elif isinstance(value, list):
        for item in value:
            values.extend(_walk_json(item))
    return values


def _unique_texts(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            unique.append(value)
    return unique


def _vigilance_content(
    *,
    update_time: str | None,
    text_items: Sequence[str],
    department_mentions: Sequence[str],
) -> str:
    lines = ["Meteo-France Vigilance bulletin for Gironde and Landes context."]
    if update_time:
        lines.append(f"Update time: {update_time}.")
    if department_mentions:
        lines.append(f"Relevant departments mentioned: {', '.join(department_mentions)}.")
    lines.extend(f"Bulletin text: {text}" for text in text_items)
    lines.append("Weather vigilance context does not replace emergency instructions.")
    return "\n".join(lines)


def _georisques_content(data: Mapping[str, object], commune_name: str, commune_code: str) -> str:
    lines = [f"Georisques risk report for {commune_name} ({commune_code})."]
    for section_name in (
        "risquesNaturels",
        "risquesTechnologiques",
        "risquesMiniers",
        "risquesParticuliers",
    ):
        section = data.get(section_name)
        if isinstance(section, dict):
            lines.extend(_georisques_section_lines(section_name, section))
    if len(lines) == 1:
        lines.append("No risk entries were parsed from the response.")
    lines.append("Risk registry context does not replace official emergency instructions.")
    return "\n".join(lines)


def _georisques_section_lines(section_name: str, section: Mapping[str, object]) -> list[str]:
    lines: list[str] = []
    for risk_id, risk_value in section.items():
        if isinstance(risk_value, dict):
            present = risk_value.get("present")
            label = _optional_text(risk_value.get("libelle")) or risk_id
            if present is True or present is None:
                lines.append(f"{section_name}: {label}.")
        elif risk_value is True:
            lines.append(f"{section_name}: {risk_id}.")
    return lines
