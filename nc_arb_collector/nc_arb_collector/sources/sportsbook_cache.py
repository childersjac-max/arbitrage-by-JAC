"""
Shared The Odds API fetcher — ONE request per sport returns all NC books.

Saves API quota: 7 sports × 1 call = 7 requests per cycle (not 7×3=21).
"""

from __future__ import annotations

from typing import Any

from ..config import NC_BOOK_KEYS, CollectorConfig
from .the_odds_api import TheOddsApiSource


class SportsbookCache:
    def __init__(self, config: CollectorConfig, api: TheOddsApiSource):
        self.config = config
        self.api = api
        self._events_by_sport: dict[str, list[dict[str, Any]]] = {}

    def events_for_sport(self, sport_key: str) -> list[dict[str, Any]]:
        if sport_key not in self._events_by_sport:
            self._events_by_sport[sport_key] = self.api.fetch_all_nc_books_single_call(sport_key)
        return self._events_by_sport[sport_key]

    def prefetch(self, sport_keys: tuple[str, ...] | None = None) -> None:
        for sport in sport_keys or self.config.sport_keys:
            self.events_for_sport(sport)

    @property
    def api_calls_made(self) -> int:
        return len(self._events_by_sport)
