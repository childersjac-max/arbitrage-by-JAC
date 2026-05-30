"""Canonical adapter for The Odds API main markets."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from harvester.adapters.base import SourceAdapter, empty_fetch_result
from harvester.baseline.odds_api_client import TheOddsApiClient
from harvester.config import HarvesterSettings
from harvester.models import MarketType, SourceQuote


MARKET_MAP: dict[str, MarketType] = {
    "h2h": MarketType.MONEYLINE,
    "spreads": MarketType.SPREAD,
    "totals": MarketType.TOTAL,
}


def _parse_datetime(value: str) -> datetime:
    """Parse provider ISO timestamps into timezone-aware UTC datetimes."""

    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


class TheOddsApiAdapter(SourceAdapter):
    """Adapter that maps The Odds API responses into `SourceQuote` objects."""

    source_id = "the_odds_api"

    def __init__(self, settings: HarvesterSettings, client: TheOddsApiClient | None = None) -> None:
        self.settings = settings
        self.client = client or TheOddsApiClient(
            api_key=settings.the_odds_api_key or "",
            timeout_seconds=settings.harvester_adapter_timeout_seconds,
        )

    async def fetch_quotes(self) -> Any:
        """Fetch configured NBA/NFL main markets from The Odds API."""

        quotes: list[SourceQuote] = []
        for sport_key in self.settings.harvester_sports:
            events = await self.client.get_odds(
                sport_key=sport_key,
                regions=self.settings.harvester_regions,
                markets=self.settings.harvester_markets,
            )
            for event in events:
                quotes.extend(self._event_to_quotes(sport_key, event))
        return empty_fetch_result(self.source_id, quotes)

    def _event_to_quotes(self, sport_key: str, event: dict[str, Any]) -> list[SourceQuote]:
        """Map one Odds API event into normalized source quote records."""

        start_time = _parse_datetime(event["commence_time"])
        home_team = event.get("home_team") or "Home"
        away_team = event.get("away_team") or "Away"
        raw_event_name = f"{away_team} @ {home_team}"
        raw_event_id = str(event.get("id") or "")
        quotes: list[SourceQuote] = []

        for bookmaker in event.get("bookmakers", []) or []:
            bookmaker_key = str(bookmaker.get("key") or bookmaker.get("title") or "bookmaker")
            source_id = f"{self.source_id}:{bookmaker_key}"
            for market in bookmaker.get("markets", []) or []:
                market_key = str(market.get("key") or "")
                market_type = MARKET_MAP.get(market_key, MarketType.OTHER)
                fetched_at = _parse_datetime(
                    market.get("last_update") or bookmaker.get("last_update") or event["commence_time"]
                )
                for outcome in market.get("outcomes", []) or []:
                    quotes.append(
                        SourceQuote(
                            source_id=source_id,
                            sport=sport_key,
                            raw_event_id=raw_event_id,
                            raw_event_name=raw_event_name,
                            start_time=start_time,
                            market_type=market_type,
                            selection_name=outcome.get("name"),
                            line=outcome.get("point"),
                            odds=outcome.get("price"),
                            url=f"https://the-odds-api.com/sports-odds-data/{sport_key}/",
                            fetched_at=fetched_at,
                            metadata={
                                "provider": "the_odds_api",
                                "bookmaker_title": bookmaker.get("title"),
                                "home_team": home_team,
                                "away_team": away_team,
                            },
                        )
                    )
        return quotes
