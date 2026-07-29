from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

from chatbot_incendie.connectors import (
    METEO_DES_FORETS_API_BASE_URL,
    MeteoDesForetsRealtimeConnector,
    UrlopenTextClient,
)
from chatbot_incendie.pipeline import run_clean_ingestion_pipeline
from chatbot_incendie.source_registry import get_source_by_id, load_sources

SOURCE_ID = "meteo-des-forets-realtime"


def main() -> int:
    api_key = os.environ.get("METEO_FRANCE_API_KEY", "")
    if not api_key:
        print("Missing METEO_FRANCE_API_KEY in the environment.")
        return 2

    base_url = os.environ.get("METEO_FRANCE_API_BASE_URL", METEO_DES_FORETS_API_BASE_URL)
    source = get_source_by_id(load_sources(Path("config/sources.toml")), SOURCE_ID)
    if source is None:
        print(f"Missing source in config/sources.toml: {SOURCE_ID}")
        return 2

    result = run_clean_ingestion_pipeline(
        source=source,
        connector=MeteoDesForetsRealtimeConnector(
            client=UrlopenTextClient(),
            api_key=api_key,
            base_url=base_url,
        ),
        output_dir=Path("data/raw"),
        collected_at=datetime.now(UTC),
    )
    print(f"Wrote {result.output_count} documents to {result.output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
