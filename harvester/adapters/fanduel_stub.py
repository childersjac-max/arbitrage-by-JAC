"""FanDuel source stub.

No scraper is implemented because sportsbook web/mobile endpoints are not a
documented public API for automated ingestion in this project.
"""

from harvester.adapters.base import NotImplementedSourceAdapter


class FanDuelStubAdapter(NotImplementedSourceAdapter):
    """Structured empty adapter for FanDuel."""

    def __init__(self) -> None:
        super().__init__(
            source_id="fanduel_direct",
            reason=(
                "source_unavailable: FanDuel direct integration requires an official "
                "documented API or explicit licensed data access."
            ),
        )
