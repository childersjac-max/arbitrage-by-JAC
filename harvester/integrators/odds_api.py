"""The Odds API (v4) — primary lawful odds source."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from config import get_settings
from integrators.base import OddsIntegrator
from models import SourceQuote, UnifiedRecord

logger = logging.getLogger(__name__)


def _parse_commence(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        text = value.replace("Z", "+00:00")
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _event_display_name(home: str, away: str) -> str:
    return f"{away} @ {home}"


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

    async def list_active_sports(self, *, all_sports: bool = False) -> list[str]:
        """Return sport keys where active==true (in-season or all catalog)."""
        settings = get_settings()
        if not settings.odds_api_key:
            raise RuntimeError("Set ODDS_API_KEY in harvester/.env or the environment")

        client = await self._get_client()
        params: dict[str, str] = {"apiKey": settings.odds_api_key}
        if all_sports:
            params["all"] = "true"
        resp = await client.get("/v4/sports", params=params)
        resp.raise_for_status()
        keys: list[str] = []
        for item in resp.json():
            if not isinstance(item, dict):
                continue
            if not item.get("active"):
                continue
            key = str(item.get("key") or "").strip()
            if key:
                keys.append(key)
        return keys

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
        return [self._event_to_record(item, sport_key) for item in payload]

    def _event_to_record(self, event: dict[str, Any], sport_key: str) -> UnifiedRecord:
        home = str(event.get("home_team") or "")
        away = str(event.get("away_team") or "")
        event_id = str(event.get("id") or f"{sport_key}:{home}:{away}")
        commence = _parse_commence(event.get("commence_time"))
        display = _event_display_name(home, away)

        by_book: dict[str, list[SourceQuote]] = {}
        for bookmaker in event.get("bookmakers") or []:
            if not isinstance(bookmaker, dict):
                continue
            book_key = str(bookmaker.get("key") or "unknown")
            book_quotes: list[SourceQuote] = []
            for market in bookmaker.get("markets") or []:
                if not isinstance(market, dict):
                    continue
                market_key = str(market.get("key") or "h2h")
                for outcome in market.get("outcomes") or []:
                    if not isinstance(outcome, dict):
                        continue
                    name = str(outcome.get("name") or "")
                    price = outcome.get("price")
                    if price is None:
                        continue
                    book_quotes.append(
                        SourceQuote(
                            source=book_key,
                            outcome=name,
                            price=float(price),
                            line=outcome.get("point"),
                            raw_label=name,
                        )
                    )
            if book_quotes:
                by_book[book_key] = book_quotes

        primary_market = "h2h"
        if by_book:
            first_book = next(iter(event.get("bookmakers") or []), {})
            if isinstance(first_book, dict) and first_book.get("markets"):
                m0 = first_book["markets"][0]
                if isinstance(m0, dict) and m0.get("key"):
                    primary_market = str(m0["key"])

        return UnifiedRecord(
            timestamp=datetime.now(timezone.utc),
            event_id=event_id,
            sport_key=sport_key,
            normalized_event_name=display,
            market_type=primary_market,
            commence_time=commence,
            sources=by_book,
            metadata={"home_team": home, "away_team": away},
        )
