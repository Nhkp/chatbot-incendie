from pathlib import Path

import pytest

from chatbot_incendie.domain import SourceStatus, SourceType
from chatbot_incendie.source_registry import get_source_by_id, load_sources


def test_load_sources_reads_project_registry() -> None:
    sources = load_sources(Path("config/sources.toml"))

    assert len(sources) == 13
    assert sources[0].id == "data-gouv-fr"
    assert sources[0].type == SourceType.OPEN_DATA
    assert sources[0].status == SourceStatus.CANDIDATE


def test_get_source_by_id_returns_matching_source() -> None:
    sources = load_sources(Path("config/sources.toml"))

    source = get_source_by_id(sources, "sdis-40")

    assert source is not None
    assert source.name == "SDIS 40"


def test_get_source_by_id_returns_none_for_unknown_source() -> None:
    sources = load_sources(Path("config/sources.toml"))

    assert get_source_by_id(sources, "missing") is None


def test_load_sources_rejects_duplicate_ids(tmp_path: Path) -> None:
    registry = tmp_path / "sources.toml"
    registry.write_text(
        """
[[sources]]
id = "duplicate"
name = "First"
type = "api"
url = "https://example.com/first"
status = "candidate"
usage_notes = "Usage notes."
rate_limit_notes = "Rate-limit notes."

[[sources]]
id = "duplicate"
name = "Second"
type = "api"
url = "https://example.com/second"
status = "candidate"
usage_notes = "Usage notes."
rate_limit_notes = "Rate-limit notes."
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="source ids must be unique: duplicate"):
        load_sources(registry)


def test_load_sources_rejects_missing_required_field(tmp_path: Path) -> None:
    registry = tmp_path / "sources.toml"
    registry.write_text(
        """
[[sources]]
id = "missing-url"
name = "Missing URL"
type = "api"
status = "candidate"
usage_notes = "Usage notes."
rate_limit_notes = "Rate-limit notes."
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="missing required fields: url"):
        load_sources(registry)


def test_load_sources_rejects_unknown_type(tmp_path: Path) -> None:
    registry = tmp_path / "sources.toml"
    registry.write_text(
        """
[[sources]]
id = "unknown-type"
name = "Unknown Type"
type = "blog"
url = "https://example.com"
status = "candidate"
usage_notes = "Usage notes."
rate_limit_notes = "Rate-limit notes."
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        load_sources(registry)
