"""The Odds API (v4) — primary lawful odds source."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from config import get_settings
from integrators.base import OddsIntegrator
from integrators.odds_events import event_dict_to_record
from models import UnifiedRecord

logger = logging.getLogger(__name__)


class OddsApiIntegrator(OddsIntegrator):
    name = "the_odds_api"

    def __init__(self, *, client: httpx.AsyncClient | None = None) -> None:
        self._client = client
        self._owns_client = client is None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            settings = get_settings()
            self._client = httpx.AsyncClient(
                base_url=settings.odds_api_base_url.rstrip("/"),
                timeout=settings.http_timeout_sec,
            )
        return self._client

    async def close(self) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    async def health_check(self) -> tuple[bool, str]:
        settings = get_settings()
        if not settings.odds_api_key:
            return False, "ODDS_API_KEY is not set"
        try:
            client = await self._get_client()
            resp = await client.get(
                "/v4/sports",
                params={"apiKey": settings.odds_api_key},
            )
            resp.raise_for_status()
            return True, f"OK ({len(resp.json())} sports listed)"
        except Exception as exc:
            return False, str(exc)

    async def fetch_records(
        self,
        sport_key: str,
        *,
        market_types: list[str] | None = None,
    ) -> list[UnifiedRecord]:
        settings = get_settings()
        if not settings.odds_api_key:
            raise RuntimeError("Set ODDS_API_KEY in harvester/.env or the environment")

        markets = ",".join(market_types) if market_types else settings.odds_api_markets
        client = await self._get_client()
        resp = await client.get(
            f"/v4/sports/{sport_key}/odds",
            params={
                "apiKey": settings.odds_api_key,
                "regions": settings.odds_api_regions,
                "markets": markets,
                "oddsFormat": settings.odds_api_odds_format,
            },
        )
        resp.raise_for_status()
        payload: list[dict[str, Any]] = resp.json()
        return [
            event_dict_to_record(
                item,
                sport_key,
                metadata_extra={"odds_source": "the_odds_api"},
            )
            for item in payload
        ]
