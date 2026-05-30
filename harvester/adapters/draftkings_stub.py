"""DraftKings source stub.

No scraper is implemented because sportsbook web/mobile endpoints are not a
documented public API for automated ingestion in this project.
"""

from harvester.adapters.base import NotImplementedSourceAdapter


class DraftKingsStubAdapter(NotImplementedSourceAdapter):
    """Structured empty adapter for DraftKings."""

    def __init__(self) -> None:
        super().__init__(
            source_id="draftkings_direct",
            reason=(
                "source_unavailable: DraftKings direct integration requires an official "
                "documented API or explicit licensed data access."
            ),
        )
