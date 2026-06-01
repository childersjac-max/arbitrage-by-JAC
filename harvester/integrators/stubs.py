"""Lawful placeholder integrators for platforms without a public API in this repo."""

from __future__ import annotations

from typing import Any

from integrators.base import OddsIntegrator
from models import UnifiedRecord

# Fourteen target platforms from the architect spec (stubs until official APIs are wired).
STUB_SPECS: list[tuple[str, str]] = [
    ("draftkings", "Use DraftKings official partner API or licensed data feed; no scraping."),
    ("fanduel", "Use FanDuel official API / affiliate data program."),
    ("betmgm", "Use BetMGM / Entain partner integrations."),
    ("caesars", "Use Caesars Sportsbook authorized API or aggregator."),
    ("betrivers", "Use Rush Street / BetRivers partner API."),
    ("pointsbet", "Use PointsBet commercial API where available."),
    ("espnbet", "Use ESPN BET / PENN partner data access."),
    ("bovada", "No public API; use licensed odds aggregator only."),
    ("bet365", "Use Bet365 affiliate / commercial feed (region-restricted)."),
    ("unibet", "Use Kindred / Unibet partner API."),
    ("pinnacle", "Use Pinnacle API (commercial; available in some regions)."),
    ("betfair", "Use Betfair Exchange API (developer.betfair.com)."),
    ("kalshi", "Use Kalshi REST API (kalshi.com/docs) for event contracts."),
    ("polymarket", "Use Polymarket CLOB / gamma API (docs.polymarket.com)."),
]


class StubIntegrator(OddsIntegrator):
    def __init__(self, platform_key: str, todo: str) -> None:
        self.name = platform_key
        self._todo = todo

    async def fetch_records(
        self,
        sport_key: str,
        *,
        market_types: list[str] | None = None,
    ) -> list[UnifiedRecord]:
        raise NotImplementedError(
            f"{self.name} adapter is not implemented. Integration path: {self._todo}"
        )

    async def health_check(self) -> tuple[bool, str]:
        return False, f"stub only — {self._todo}"

    def integration_notes(self) -> dict[str, Any]:
        return {
            "integrator": self.name,
            "status": "stub",
            "integration_path": self._todo,
        }


def get_stub_integrator(platform_key: str) -> StubIntegrator:
    for key, todo in STUB_SPECS:
        if key == platform_key:
            return StubIntegrator(key, todo)
    raise KeyError(f"Unknown stub platform: {platform_key}")


STUB_INTEGRATORS: dict[str, StubIntegrator] = {
    key: StubIntegrator(key, todo) for key, todo in STUB_SPECS
}
