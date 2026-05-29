"""
The Odds API — licensed aggregator for US sportsbooks including DK, FD, BetMGM.

https://the-odds-api.com — requires ODDS_API_KEY. This is the compliant path for
NC-legal mobile sportsbook lines without scraping operator sites.
"""

from __future__ import annotations

from typing import Any, Iterable

from ..config import CollectorConfig, NC_BOOK_KEYS
from ..http.client import ResilientHttpClient


class TheOddsApiSource:
    BASE = "https://api.the-odds-api.com/v4"

    def __init__(self, config: CollectorConfig, http: ResilientHttpClient):
        self.config = config
        self.http = http
        self.api_key = config.odds_api_key

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def fetch_events_for_book(
        self,
        sport_key: str,
        book_key: str,
        markets: Iterable[str] | None = None,
    ) -> list[dict[str, Any]]:
        if not self.enabled:
            return []
        markets = list(markets) if markets else list(self.config.markets)
        params = {
            "apiKey": self.api_key,
            "regions": "us",
            "markets": ",".join(markets),
            "oddsFormat": "american",
            "bookmakers": book_key,
        }
        url = f"{self.BASE}/sports/{sport_key}/odds"
        data = self.http.get_json(url, params=params)
        if isinstance(data, list):
            return data
        return []

    def fetch_all_nc_books_single_call(self, sport_key: str) -> list[dict[str, Any]]:
        """
        Single API request returns events with draftkings, fanduel, betmgm bookmakers.
        This is the recommended path to conserve monthly quota.
        """
        if not self.enabled:
            return []
        markets = list(self.config.markets)
        params = {
            "apiKey": self.api_key,
            "regions": "us",
            "markets": ",".join(markets),
            "oddsFormat": "american",
            "bookmakers": ",".join(NC_BOOK_KEYS),
        }
        url = f"{self.BASE}/sports/{sport_key}/odds"
        data = self.http.get_json(url, params=params)
        if isinstance(data, list):
            return data
        return []

    def fetch_all_nc_books(self, sport_key: str) -> dict[str, list[dict[str, Any]]]:
        events = self.fetch_all_nc_books_single_call(sport_key)
        out: dict[str, list[dict[str, Any]]] = {book: events for book in NC_BOOK_KEYS}
        return out
