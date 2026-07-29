from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from urllib.parse import urlparse


class SourceType(StrEnum):
    API = "api"
    OFFICIAL_WEBSITE = "official_website"
    NEWS = "news"
    WEATHER = "weather"
    OPEN_DATA = "open_data"
    OTHER = "other"


class SourceStatus(StrEnum):
    CANDIDATE = "candidate"
    APPROVED = "approved"
    DISABLED = "disabled"
    OPTIONAL = "optional"


@dataclass(frozen=True)
class Source:
    id: str
    name: str
    type: SourceType
    url: str
    status: SourceStatus
    usage_notes: str
    rate_limit_notes: str

    def __post_init__(self) -> None:
        _require_text(self.id, "source id")
        _require_text(self.name, "source name")
        _require_http_url(self.url)
        _require_text(self.usage_notes, "usage notes")
        _require_text(self.rate_limit_notes, "rate-limit notes")


@dataclass(frozen=True)
class RawDocument:
    source_id: str
    url: str
    content: str
    title: str | None = None
    canonical_url: str | None = None
    published_at: datetime | None = None
    collected_at: datetime | None = None

    def __post_init__(self) -> None:
        _require_text(self.source_id, "source id")
        _require_http_url(self.url)
        _require_text(self.content, "document content")
        if self.canonical_url is not None:
            _require_http_url(self.canonical_url)


def _require_text(value: str, label: str) -> None:
    if not value.strip():
        raise ValueError(f"{label} must not be empty")


def _require_http_url(value: str) -> None:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"url must be HTTP(S): {value}")
