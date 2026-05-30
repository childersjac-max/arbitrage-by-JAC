"""Async client for The Odds API v4.

The paid The Odds API subscription is the only paid data source used by this
harvester. Endpoints implemented here are documented public provider APIs:

* GET /v4/sports
* GET /v4/sports/{sport_key}/events
* GET /v4/sports/{sport_key}/odds
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import httpx

from harvester.adapters.base import SourceAdapterError, SourceTransientError


class TheOddsApiClient:
    """Small typed wrapper around The Odds API v4 HTTP endpoints."""

    base_url = "https://api.the-odds-api.com/v4"

    def __init__(self, api_key: str, timeout_seconds: float = 15.0) -> None:
        if not api_key:
            raise ValueError("THE_ODDS_API_KEY is required")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """Issue a GET request and return decoded JSON."""

        query = dict(params or {})
        query["apiKey"] = self.api_key
        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout_seconds) as client:
            response = await client.get(path, params=query)
        if response.status_code == 429 or response.status_code >= 500:
            raise SourceTransientError(
                f"The Odds API transient HTTP {response.status_code}: {response.text[:250]}"
            )
        if response.status_code >= 400:
            raise SourceAdapterError(
                f"The Odds API HTTP {response.status_code}: {response.text[:250]}"
            )
        return response.json()

    async def get_sports(self) -> list[dict[str, Any]]:
        """Return available sports from The Odds API."""

        data = await self._get("/sports")
        return data if isinstance(data, list) else []

    async def get_events(self, sport_key: str) -> list[dict[str, Any]]:
        """Return events for one sport key."""

        data = await self._get(f"/sports/{sport_key}/events")
        return data if isinstance(data, list) else []

    async def get_odds(
        self,
        sport_key: str,
        regions: str,
        markets: Iterable[str],
        bookmakers: Iterable[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Return main-market odds for one sport key."""

        params: dict[str, Any] = {
            "regions": regions,
            "markets": ",".join(markets),
            "oddsFormat": "american",
            "dateFormat": "iso",
        }
        if bookmakers:
            params["bookmakers"] = ",".join(bookmakers)
        data = await self._get(f"/sports/{sport_key}/odds", params)
        return data if isinstance(data, list) else []
