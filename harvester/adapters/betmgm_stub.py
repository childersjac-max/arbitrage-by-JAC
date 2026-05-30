"""BetMGM source stub.

No scraper is implemented because sportsbook web/mobile endpoints are not a
documented public API for automated ingestion in this project.
"""

from harvester.adapters.base import NotImplementedSourceAdapter


class BetMgmStubAdapter(NotImplementedSourceAdapter):
    """Structured empty adapter for BetMGM."""

    def __init__(self) -> None:
        super().__init__(
            source_id="betmgm_direct",
            reason=(
                "source_unavailable: BetMGM direct integration requires an official "
                "documented API or explicit licensed data access."
            ),
        )
