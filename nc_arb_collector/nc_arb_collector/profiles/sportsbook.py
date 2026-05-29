"""Shared sportsbook profile logic — reads from SportsbookCache (1 API call/sport)."""

from __future__ import annotations

from typing import Any

from ..models import MarketPacket, OddsLeg
from ..sources.sportsbook_cache import SportsbookCache
from ..sources.the_odds_api import TheOddsApiSource
from ..utils.odds_math import american_to_implied_prob
from .base import ExtractionProfile


def events_to_packets(
    events: list[dict[str, Any]],
    platform_key: str,
    book_title: str,
) -> list[MarketPacket]:
    packets: list[MarketPacket] = []
    for ev in events:
        event_id = ev.get("id") or ""
        home = ev.get("home_team") or ""
        away = ev.get("away_team") or ""
        commence = ev.get("commence_time")
        for bm in ev.get("bookmakers") or []:
            if bm.get("key") != platform_key and bm.get("title", "").lower() != book_title.lower():
                continue
            for market in bm.get("markets") or []:
                mkey = market.get("key") or "h2h"
                legs: list[OddsLeg] = []
                for outcome in market.get("outcomes") or []:
                    price = outcome.get("price")
                    if price is None:
                        continue
                    name = outcome.get("name") or ""
                    point = outcome.get("point")
                    legs.append(
                        OddsLeg(
                            platform=platform_key,
                            outcome_key=name,
                            american_odds=float(price),
                            line=float(point) if point is not None else None,
                            implied_prob=american_to_implied_prob(float(price)),
                            raw=outcome,
                        )
                    )
                if not legs:
                    continue
                packets.append(
                    MarketPacket(
                        source_platform=platform_key,
                        event_key=f"{platform_key}:{event_id}:{mkey}",
                        home_team=home,
                        away_team=away,
                        market_type=mkey,
                        commence_time=commence,
                        legs=legs,
                        metadata={"bookmaker": bm.get("title"), "event_id": event_id},
                    )
                )
    return packets


class SportsbookProfile(ExtractionProfile):
    def __init__(
        self,
        config,
        http,
        *,
        platform_key: str,
        display_name: str,
        cache: SportsbookCache | None = None,
    ):
        super().__init__(config, http)
        self.platform_key = platform_key
        self.display_name = display_name
        self._cache = cache

    def extract(self, sport_keys: tuple[str, ...] | None = None) -> list[MarketPacket]:
        keys = sport_keys or self.config.sport_keys
        cache = self._cache
        if cache is None or not cache.api.enabled:
            return []
        out: list[MarketPacket] = []
        for sport in keys:
            events = cache.events_for_sport(sport)
            out.extend(events_to_packets(events, self.platform_key, self.display_name))
        return out
