"""
Aggregation & splice engine — merges fragmented packets from all profiles,
fills gaps by cross-source matching, and produces unified markets.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from ..models import MarketPacket, OddsLeg, UnifiedMarket
from .normalize import (
    event_match_key,
    match_outcome_names,
    normalize_market_type,
    normalized_event_display,
    teams_match,
)  # noqa: F401 — match_outcome_names used in _merge_packet


class SpliceEngine:
    """
    COMPETE DATA PIECING: sportsbook lines (fast, structured) splice with
    prediction-market contracts (event metadata, alt phrasing) via fuzzy keys.
    """

    def __init__(self):
        self._by_key: dict[str, UnifiedMarket] = {}

    def ingest_packets(self, packets: list[MarketPacket]) -> None:
        for pkt in packets:
            self._merge_packet(pkt)

    def _merge_packet(self, pkt: MarketPacket) -> None:
        mtype = normalize_market_type(pkt.market_type)
        key = event_match_key(pkt.home_team, pkt.away_team, mtype)
        existing = self._by_key.get(key)

        if existing is None:
            # Try fuzzy attach to prediction-market style titles
            for ek, um in self._by_key.items():
                if um.market_type != mtype:
                    continue
                if teams_match(pkt.home_team, pkt.away_team, um.home_team, um.away_team):
                    existing = um
                    key = ek
                    break
            if existing is None:
                # Fuzzy scan on display name
                for ek, um in self._by_key.items():
                    if um.market_type != mtype:
                        continue
                    parts = ek.split("|")
                    if len(parts) >= 2 and teams_match(
                        pkt.home_team, pkt.away_team, parts[0], parts[1]
                    ):
                        existing = um
                        key = ek
                        break

        if existing is None:
            legs_map: dict[str, list[OddsLeg]] = {pkt.source_platform: list(pkt.legs)}
            self._by_key[key] = UnifiedMarket(
                normalized_event_name=normalized_event_display(pkt.home_team, pkt.away_team),
                market_type=mtype,
                commence_time=pkt.commence_time,
                home_team=pkt.home_team,
                away_team=pkt.away_team,
                legs_by_platform=legs_map,
                event_key=key,
                splice_sources=[pkt.source_platform],
            )
            return

        bucket = existing.legs_by_platform.setdefault(pkt.source_platform, [])
        for leg in pkt.legs:
            replaced = False
            for i, prev in enumerate(bucket):
                if match_outcome_names(prev.outcome_key, leg.outcome_key):
                    if (leg.implied_prob or 0) >= (prev.implied_prob or 0):
                        bucket[i] = leg
                    replaced = True
                    break
            if not replaced:
                bucket.append(leg)
        if pkt.source_platform not in existing.splice_sources:
            existing.splice_sources.append(pkt.source_platform)
        if not existing.commence_time and pkt.commence_time:
            existing.commence_time = pkt.commence_time

    def unified_markets(self) -> list[UnifiedMarket]:
        return list(self._by_key.values())

    def gap_fill_report(self) -> dict[str, int]:
        """How many markets have 1 vs 2+ platform legs (diagnostic)."""
        single = multi = 0
        for um in self._by_key.values():
            n = len(um.legs_by_platform)
            if n >= 2:
                multi += 1
            else:
                single += 1
        return {"single_source": single, "multi_source": multi, "total": single + multi}

    def snapshot(self) -> dict:
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "stats": self.gap_fill_report(),
            "markets": [
                {
                    "normalized_event_name": um.normalized_event_name,
                    "market_type": um.market_type,
                    "commence_time": um.commence_time,
                    "sources": um.splice_sources,
                    "platforms": {
                        plat: [
                            {
                                "american_odds": leg.american_odds,
                                "outcome": leg.outcome_key,
                                "line": leg.line,
                            }
                            for leg in legs
                        ]
                        for plat, legs in um.legs_by_platform.items()
                    },
                }
                for um in self.unified_markets()
            ],
        }
