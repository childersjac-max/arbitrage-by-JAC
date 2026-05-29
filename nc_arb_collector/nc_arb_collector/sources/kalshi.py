"""Kalshi public Trade API — no authentication required for market data."""

from __future__ import annotations

import re
from typing import Any

from ..config import CollectorConfig
from ..http.client import ResilientHttpClient
from ..models import MarketPacket, OddsLeg
from ..utils.odds_math import prob_cents_to_american


# Game-level Kalshi series (free public API) — more precise than generic /markets
KALSHI_SPORTS_SERIES = (
    "KXNFLGAME",
    "KXNBAGAME",
    "KXMLBGAME",
    "KXNHLGAME",
    "KXNCAAFGAME",
    "KXNCAAMBGAME",
    "KXWNBAGAME",
    "KXUFCFIGHT",
    "KXSOCCERGAME",
)


class KalshiSource:
    SPORTS_HINT = re.compile(
        r"\b(vs\.?|beat|winner|wins?|nfl|nba|mlb|nhl|ncaa|college|super bowl|"
        r"playoff|championship|touchdown|rebounds?|assists?|points?|spread|"
        r"moneyline|mlb|wnba|ufc|mma|soccer|mls)\b|:\s*\d+\+",
        re.I,
    )

    def __init__(self, config: CollectorConfig, http: ResilientHttpClient):
        self.config = config
        self.http = http

    def fetch_open_markets(self, limit: int = 500) -> list[dict[str, Any]]:
        """Prefer sports game series; fall back to open markets scan."""
        by_ticker: dict[str, dict[str, Any]] = {}
        for series in KALSHI_SPORTS_SERIES:
            for m in self._fetch_series_markets(series, limit=200):
                t = m.get("ticker")
                if t:
                    by_ticker[t] = m
        if by_ticker:
            return list(by_ticker.values())[:limit]
        return self._fetch_open_markets_paginated(limit)

    def _fetch_series_markets(self, series_ticker: str, limit: int = 200) -> list[dict[str, Any]]:
        url = f"{self.config.kalshi_base_url}/markets"
        data = self.http.get_json(
            url,
            params={"status": "open", "series_ticker": series_ticker, "limit": limit},
        )
        if isinstance(data, dict):
            return data.get("markets") or []
        return []

    def _fetch_open_markets_paginated(self, limit: int = 500) -> list[dict[str, Any]]:
        url = f"{self.config.kalshi_base_url}/markets"
        all_markets: list[dict[str, Any]] = []
        cursor: str | None = None
        pages = 0
        while pages < 10 and len(all_markets) < limit:
            params: dict[str, Any] = {"status": "open", "limit": min(200, limit)}
            if cursor:
                params["cursor"] = cursor
            data = self.http.get_json(url, params=params)
            if not isinstance(data, dict):
                break
            batch = data.get("markets") or []
            all_markets.extend(batch)
            cursor = data.get("cursor") or ""
            if not cursor or not batch:
                break
            pages += 1
        return all_markets

    def to_packets(self, markets: list[dict[str, Any]]) -> list[MarketPacket]:
        packets: list[MarketPacket] = []
        for m in markets:
            title = (m.get("title") or "").strip()
            if not title or not self.SPORTS_HINT.search(title):
                continue
            yes_cents = m.get("yes_ask") or m.get("yes_bid")
            if yes_cents is None:
                for field in ("yes_ask_dollars", "yes_bid_dollars", "last_price_dollars"):
                    raw = m.get(field)
                    if raw is not None:
                        try:
                            yes_cents = float(raw) * 100.0
                            break
                        except (TypeError, ValueError):
                            continue
            if yes_cents is None:
                continue
            american = prob_cents_to_american(float(yes_cents))
            teams = self._parse_teams(title)
            home, away = teams if teams else ("", "")
            event_key = f"kalshi:{m.get('ticker', title)}"
            packets.append(
                MarketPacket(
                    source_platform="kalshi",
                    event_key=event_key,
                    home_team=home or title,
                    away_team=away or "field",
                    market_type="h2h",
                    commence_time=m.get("close_time"),
                    legs=[
                        OddsLeg(
                            platform="kalshi",
                            outcome_key="yes",
                            american_odds=american,
                            raw=m,
                        )
                    ],
                    metadata={"ticker": m.get("ticker"), "title": title},
                )
            )
        return packets

    @staticmethod
    def _parse_teams(title: str) -> tuple[str, str] | None:
        for sep in (" vs. ", " vs ", " beat ", " to beat "):
            if sep in title.lower():
                parts = re.split(re.escape(sep), title, maxsplit=1, flags=re.I)
                if len(parts) == 2:
                    return parts[0].strip(), parts[1].strip()
        return None
