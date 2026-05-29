"""
Kalshi regulated prediction market — public Trade API v2.

Docs: https://trading-api.readme.io/reference/getmarkets
No authentication required for market listings and order books.
"""

from __future__ import annotations

import re
from typing import Any

from arb_harvest.models import MarketQuote, NormalizedEvent, OutcomeQuote, SourceBook
from arb_harvest.net import PoliteHttpClient
from arb_harvest.normalize.matcher import normalize_team_token
from arb_harvest.normalize.sport_infer import infer_sport_key
from arb_harvest.scrape.base import SupplementalFetcher

KALSHI_BASE = "https://api.elections.kalshi.com/trade-api/v2"


def _prob_cents_to_american(cents: float) -> int:
    p = cents / 100.0
    if p <= 0 or p >= 1:
        return 100
    if p >= 0.5:
        return int(round(-(p / (1 - p)) * 100))
    return int(round(((1 - p) / p) * 100))


def _parse_teams_from_title(title: str) -> tuple[str, str] | None:
    t = title.strip()
    for sep in (" vs ", " vs. ", " beat ", " to beat ", " @ "):
        if sep in t.lower():
            parts = re.split(re.escape(sep), t, maxsplit=1, flags=re.I)
            if len(parts) == 2:
                return parts[0].strip(), parts[1].strip()
    return None


class KalshiFetcher(SupplementalFetcher):
    source_id = "kalshi"

    def __init__(self, http: PoliteHttpClient):
        self.http = http

    def _markets(self, limit: int = 250) -> list[dict[str, Any]]:
        data = self.http.get_json(
            f"{KALSHI_BASE}/markets",
            params={"status": "open", "limit": limit},
        )
        if not isinstance(data, dict):
            return []
        return list(data.get("markets") or [])

    def _orderbook_depth(self, ticker: str) -> float | None:
        data = self.http.get_json(f"{KALSHI_BASE}/markets/{ticker}/orderbook")
        if not isinstance(data, dict):
            return None
        ob = data.get("orderbook") or data
        yes_bids = (ob.get("yes") or ob.get("yes_dollars") or []) if isinstance(ob, dict) else []
        total = 0.0
        for level in yes_bids[:5]:
            if isinstance(level, (list, tuple)) and len(level) >= 2:
                total += float(level[1])
        return total if total > 0 else None

    def fetch(self) -> list[NormalizedEvent]:
        events: list[NormalizedEvent] = []
        for m in self._markets():
            title = m.get("title") or ""
            if not title:
                continue
            teams = _parse_teams_from_title(title)
            if not teams:
                continue
            home_raw, away_raw = teams
            yes_cents = m.get("yes_ask") or m.get("yes_bid")
            if yes_cents is None:
                continue
            ticker = m.get("ticker", "")
            volume = self._orderbook_depth(ticker) if ticker else None
            price = _prob_cents_to_american(float(yes_cents))
            sport_key = infer_sport_key(title)
            home = normalize_team_token(home_raw, sport_key)
            away = normalize_team_token(away_raw, sport_key)
            outcome = OutcomeQuote(
                name=title,
                price_american=price,
                volume=volume,
            )
            book = SourceBook(
                source_id=self.source_id,
                title="Kalshi",
                markets=[
                    MarketQuote(
                        key="binary_yes",
                        outcomes=[outcome],
                        last_update=m.get("close_time"),
                    )
                ],
                raw=m,
            )
            events.append(
                NormalizedEvent(
                    event_id=ticker or title,
                    sport_key=sport_key,
                    normalized_name="",
                    home_team=home_raw,
                    away_team=away_raw,
                    commence_time=m.get("close_time") or "",
                    books=[book],
                )
            )
        return events
