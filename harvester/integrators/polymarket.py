"""
Polymarket integrator — public Gamma + CLOB APIs (no API key).

Docs:
  - Market metadata: https://gamma-api.polymarket.com
  - Order books:     https://clob.polymarket.com/book?token_id=...

Prices from Gamma ``outcomePrices`` are implied probabilities (0–1).
We convert to decimal odds as ``1 / p`` for the arbitrage engine.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from config import get_settings
from integrators.base import OddsIntegrator
from models import SourceQuote, UnifiedRecord

logger = logging.getLogger(__name__)

PLATFORM_KEY = "polymarket"

# Map harvester sport_key → keywords matched in question / slug (lowercase).
SPORT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "basketball_nba": ("nba", "basketball"),
    "americanfootball_nfl": ("nfl", "super bowl", "football"),
    "baseball_mlb": ("mlb", "baseball", "world series"),
    "icehockey_nhl": ("nhl", "hockey", "stanley cup"),
    "soccer_epl": ("premier league", "epl", "soccer"),
    "mma_mixed_martial_arts": ("ufc", "mma"),
}


def parse_json_list_field(raw: Any) -> list[Any]:
    """Gamma returns outcomes / prices / token ids as JSON strings or lists."""
    if raw is None:
        return []
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
            return parsed if isinstance(parsed, list) else []
        except json.JSONDecodeError:
            return []
    return []


def probability_to_decimal_odds(probability: float) -> float | None:
    """Convert implied probability (0–1) to decimal odds (>1)."""
    if probability <= 0.0 or probability >= 1.0:
        return None
    return round(1.0 / probability, 6)


def normalize_polymarket_market(market: dict[str, Any]) -> dict[str, Any]:
    """Normalize raw Gamma market dict to an internal shape (for tests / debugging)."""
    outcomes = parse_json_list_field(market.get("outcomes"))
    prices = parse_json_list_field(market.get("outcomePrices"))
    token_ids = parse_json_list_field(market.get("clobTokenIds"))

    normalized_outcomes: list[dict[str, Any]] = []
    for idx, name in enumerate(outcomes):
        entry: dict[str, Any] = {"name": str(name)}
        if idx < len(token_ids):
            entry["token_id"] = str(token_ids[idx])
        if idx < len(prices):
            try:
                entry["probability"] = float(prices[idx])
            except (TypeError, ValueError):
                pass
        normalized_outcomes.append(entry)

    condition_id = (
        market.get("conditionId")
        or market.get("condition_id")
        or market.get("id")
        or ""
    )

    return {
        "event_id": str(condition_id),
        "event_name": str(market.get("question") or market.get("title") or ""),
        "platform": PLATFORM_KEY,
        "slug": market.get("slug"),
        "outcomes": normalized_outcomes,
        "active": bool(market.get("active", False)),
        "closed": bool(market.get("closed", True)),
    }


def market_matches_sport(market: dict[str, Any], sport_key: str) -> bool:
    """Keyword filter — Polymarket has no sport_key param on Gamma."""
    keywords = SPORT_KEYWORDS.get(sport_key)
    if not keywords:
        return True
    haystack = " ".join(
        str(market.get(key) or "")
        for key in ("question", "slug", "description", "groupItemTitle")
    ).lower()
    tags = market.get("tags") or []
    if isinstance(tags, list):
        haystack += " " + " ".join(str(t).lower() for t in tags)
    return any(kw in haystack for kw in keywords)


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        text = value.replace("Z", "+00:00")
        return datetime.fromisoformat(text)
    except ValueError:
        return None


class PolymarketIntegrator(OddsIntegrator):
    name = PLATFORM_KEY

    def __init__(self, *, client: httpx.AsyncClient | None = None) -> None:
        self._client = client
        self._owns_client = client is None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            settings = get_settings()
            self._client = httpx.AsyncClient(
                timeout=settings.http_timeout_sec,
                headers={
                    "Accept": "application/json",
                    "User-Agent": settings.http_user_agent,
                },
            )
        return self._client

    async def close(self) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    async def health_check(self) -> tuple[bool, str]:
        try:
            markets = await self._fetch_gamma_markets(limit=1, offset=0)
            return True, f"OK ({len(markets)} market sample)"
        except Exception as exc:
            return False, str(exc)

    def integration_notes(self) -> dict[str, Any]:
        settings = get_settings()
        return {
            "integrator": self.name,
            "status": "live" if settings.polymarket_enabled else "disabled",
            "gamma_base_url": settings.polymarket_gamma_base_url,
            "use_orderbook": settings.polymarket_use_orderbook,
        }

    async def _fetch_gamma_markets(self, *, limit: int, offset: int) -> list[dict[str, Any]]:
        settings = get_settings()
        client = await self._get_client()
        resp = await client.get(
            f"{settings.polymarket_gamma_base_url.rstrip('/')}/markets",
            params={
                "limit": limit,
                "offset": offset,
                "closed": "false",
                "active": "true",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list):
            return [m for m in data if isinstance(m, dict)]
        if isinstance(data, dict):
            inner = data.get("data") or data.get("markets") or []
            return [m for m in inner if isinstance(m, dict)]
        return []

    async def _best_bid_decimal(self, token_id: str) -> float | None:
        """Optional: best bid from CLOB as decimal odds."""
        settings = get_settings()
        client = await self._get_client()
        resp = await client.get(
            f"{settings.polymarket_clob_base_url.rstrip('/')}/book",
            params={"token_id": token_id},
        )
        resp.raise_for_status()
        book = resp.json()
        bids = book.get("bids") or []
        best_prob = 0.0
        for level in bids:
            if not isinstance(level, dict):
                continue
            try:
                prob = float(level.get("price") or 0)
            except (TypeError, ValueError):
                continue
            if prob > best_prob:
                best_prob = prob
        return probability_to_decimal_odds(best_prob) if best_prob > 0 else None

    async def fetch_records(
        self,
        sport_key: str,
        *,
        market_types: list[str] | None = None,
    ) -> list[UnifiedRecord]:
        settings = get_settings()
        if not settings.polymarket_enabled:
            return []

        limit = settings.polymarket_market_limit
        markets = await self._fetch_gamma_markets(limit=limit, offset=0)

        records: list[UnifiedRecord] = []
        for raw in markets:
            if raw.get("closed") or not raw.get("active", True):
                continue
            if not market_matches_sport(raw, sport_key):
                continue

            record = await self._market_to_record(raw, sport_key, use_orderbook=settings.polymarket_use_orderbook)
            if record is not None:
                records.append(record)

        logger.info("Polymarket: %s records for sport=%s", len(records), sport_key)
        return records

    async def _market_to_record(
        self,
        market: dict[str, Any],
        sport_key: str,
        *,
        use_orderbook: bool,
    ) -> UnifiedRecord | None:
        norm = normalize_polymarket_market(market)
        if not norm["event_id"] or not norm["event_name"]:
            return None

        quotes: list[SourceQuote] = []
        for outcome in norm["outcomes"]:
            name = str(outcome.get("name") or "")
            token_id = outcome.get("token_id")
            decimal_price: float | None = None

            if use_orderbook and token_id:
                try:
                    decimal_price = await self._best_bid_decimal(str(token_id))
                except Exception as exc:
                    logger.debug("Polymarket orderbook %s: %s", token_id, exc)

            if decimal_price is None and outcome.get("probability") is not None:
                decimal_price = probability_to_decimal_odds(float(outcome["probability"]))

            if decimal_price is None or decimal_price <= 1.0:
                continue

            quotes.append(
                SourceQuote(
                    source=PLATFORM_KEY,
                    outcome=name,
                    price=decimal_price,
                    raw_label=name,
                )
            )

        if not quotes:
            return None

        commence = _parse_iso_datetime(
            market.get("endDate") or market.get("gameStartTime") or market.get("startDate")
        )

        return UnifiedRecord(
            timestamp=datetime.now(timezone.utc),
            event_id=f"polymarket:{norm['event_id']}",
            sport_key=sport_key,
            normalized_event_name=norm["event_name"],
            market_type="binary",
            commence_time=commence,
            sources={PLATFORM_KEY: quotes},
            metadata={
                "platform": PLATFORM_KEY,
                "slug": norm.get("slug"),
                "condition_id": norm["event_id"],
                "gamma_id": market.get("id"),
            },
        )
