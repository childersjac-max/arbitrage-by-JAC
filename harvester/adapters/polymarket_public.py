"""Optional adapter for Polymarket's documented public CLOB API."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from harvester.adapters.base import SourceAdapter, SourceAdapterError, SourceTransientError, empty_fetch_result
from harvester.config import HarvesterSettings
from harvester.models import MarketType, SourceQuote


def _utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""

    return datetime.now(timezone.utc)


class PolymarketPublicAdapter(SourceAdapter):
    """Read active public binary markets from Polymarket's CLOB API.

    This adapter uses only the documented public HTTP API and does not require
    paid data or privileged credentials. It is disabled by default because the
    market taxonomy is broad and should be filtered for the arb app's domain.
    """

    source_id = "polymarket_public"

    def __init__(self, settings: HarvesterSettings) -> None:
        self.settings = settings

    async def fetch_quotes(self) -> Any:
        """Fetch a small page of public markets and map yes/no prices."""

        timeout = self.settings.harvester_adapter_timeout_seconds
        async with httpx.AsyncClient(base_url=self.settings.polymarket_clob_base_url, timeout=timeout) as client:
            response = await client.get("/markets", params={"next_cursor": ""})
        if response.status_code == 429 or response.status_code >= 500:
            raise SourceTransientError(
                f"Polymarket public API transient HTTP {response.status_code}: {response.text[:250]}"
            )
        if response.status_code >= 400:
            raise SourceAdapterError(
                f"Polymarket public API HTTP {response.status_code}: {response.text[:250]}"
            )
        payload = response.json()
        markets = payload.get("data", payload if isinstance(payload, list) else [])
        quotes = [quote for market in markets[:100] for quote in self._market_to_quotes(market)]
        return empty_fetch_result(self.source_id, quotes)

    def _market_to_quotes(self, market: dict[str, Any]) -> list[SourceQuote]:
        """Convert one public CLOB market payload into binary source quotes."""

        if market.get("closed") or market.get("active") is False:
            return []

        question = str(market.get("question") or market.get("description") or market.get("condition_id") or "")
        if not question:
            return []

        raw_event_id = str(market.get("condition_id") or market.get("market_slug") or question)
        end_time = market.get("end_date_iso") or market.get("endDate") or market.get("game_start_time")
        try:
            start_time = (
                datetime.fromisoformat(str(end_time).replace("Z", "+00:00")).astimezone(timezone.utc)
                if end_time
                else _utc_now()
            )
        except ValueError:
            start_time = _utc_now()

        fetched_at = _utc_now()
        liquidity = _safe_float(market.get("liquidity"))
        volume = _safe_float(market.get("volume"))
        quotes: list[SourceQuote] = []

        for token in market.get("tokens", []) or []:
            outcome = str(token.get("outcome") or "").strip()
            price = _safe_float(token.get("price") or token.get("midpoint"))
            if not outcome or price is None:
                continue
            quotes.append(
                SourceQuote(
                    source_id=self.source_id,
                    sport="prediction_market",
                    raw_event_id=raw_event_id,
                    raw_event_name=question,
                    start_time=start_time,
                    market_type=MarketType.BINARY_YES_NO,
                    selection_name=outcome,
                    odds=price,
                    volume=volume,
                    liquidity=liquidity,
                    url=market.get("url"),
                    fetched_at=fetched_at,
                    metadata={"provider": "polymarket_public"},
                )
            )
        return quotes


def _safe_float(value: Any) -> float | None:
    """Best-effort float conversion for public API fields."""

    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None
