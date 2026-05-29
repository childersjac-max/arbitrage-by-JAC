"""Polymarket Gamma API — free, no auth (sports via public-search + events)."""

from __future__ import annotations

import json
import re
from typing import Any

from ..config import CollectorConfig
from ..http.client import ResilientHttpClient
from ..models import MarketPacket, OddsLeg
from ..utils.odds_math import predictit_price_to_american

GAMMA_BASE = "https://gamma-api.polymarket.com"

# Queries that surface game-level sports markets on Polymarket
SPORTS_SEARCH_QUERIES = (
    "NBA",
    "NFL",
    "MLB",
    "NHL",
    "NCAA basketball",
    "NCAA football",
    "Super Bowl",
    "Stanley Cup",
    "World Series",
)


class PolymarketSource:
    SPORTS_TITLE = re.compile(
        r"\b(vs\.?|beat|winner|champion|playoff|draft|mvp|game \d|"
        r"super bowl|world series|stanley cup|nba|nfl|mlb|nhl|ncaa)\b",
        re.I,
    )

    def __init__(self, config: CollectorConfig, http: ResilientHttpClient):
        self.config = config
        self.http = http

    def fetch_sports_events(self) -> list[dict[str, Any]]:
        seen: set[str] = set()
        events: list[dict[str, Any]] = []
        for q in SPORTS_SEARCH_QUERIES:
            data = self.http.get_json(
                f"{GAMMA_BASE}/public-search",
                params={
                    "q": q,
                    "events_status": "active",
                    "limit_per_type": 25,
                },
            )
            if not isinstance(data, dict):
                continue
            for ev in data.get("events") or []:
                eid = str(ev.get("id") or ev.get("slug") or "")
                if not eid or eid in seen:
                    continue
                title = ev.get("title") or ""
                if not self.SPORTS_TITLE.search(title):
                    continue
                seen.add(eid)
                events.append(ev)
        return events

    def to_packets(self, events: list[dict[str, Any]]) -> list[MarketPacket]:
        packets: list[MarketPacket] = []
        for ev in events:
            title = ev.get("title") or ""
            markets = ev.get("markets") or []
            for m in markets:
                prices_raw = m.get("outcomePrices")
                outcomes_raw = m.get("outcomes")
                if not prices_raw or not outcomes_raw:
                    continue
                try:
                    prices = json.loads(prices_raw) if isinstance(prices_raw, str) else prices_raw
                    outcomes = json.loads(outcomes_raw) if isinstance(outcomes_raw, str) else outcomes_raw
                except (json.JSONDecodeError, TypeError):
                    continue
                if not isinstance(prices, list) or not isinstance(outcomes, list):
                    continue
                legs: list[OddsLeg] = []
                for name, pstr in zip(outcomes, prices):
                    try:
                        p = float(pstr)
                    except (TypeError, ValueError):
                        continue
                    american = predictit_price_to_american(p)
                    legs.append(
                        OddsLeg(
                            platform="polymarket",
                            outcome_key=str(name),
                            american_odds=american,
                            raw={"price": p, "question": m.get("question")},
                        )
                    )
                if not legs:
                    continue
                home, away = self._split_title(title)
                packets.append(
                    MarketPacket(
                        source_platform="polymarket",
                        event_key=f"polymarket:{ev.get('id')}:{m.get('id')}",
                        home_team=home,
                        away_team=away,
                        market_type="h2h",
                        commence_time=ev.get("endDate") or m.get("endDate"),
                        legs=legs,
                        metadata={"event_title": title, "question": m.get("question")},
                    )
                )
        return packets

    @staticmethod
    def _split_title(title: str) -> tuple[str, str]:
        for sep in (" vs. ", " vs ", " @ ", " at "):
            if sep in title.lower():
                parts = re.split(re.escape(sep), title, maxsplit=1, flags=re.I)
                if len(parts) == 2:
                    return parts[0].strip(), parts[1].strip()
        return title, ""
