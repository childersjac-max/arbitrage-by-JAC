"""
Arbitrage detection on unified markets — cross-book and sportsbook vs prediction market.
"""

from __future__ import annotations

from datetime import datetime, timezone
from itertools import combinations
from typing import Iterable

from ..models import ArbitrageRow, UnifiedMarket
from ..utils.odds_math import american_to_implied_prob, two_way_arb_yield
from .normalize import match_outcome_names


class ArbitragePipeline:
    def __init__(self, min_yield_pct: float = 0.5):
        self.min_yield_pct = min_yield_pct

    def scan(self, markets: Iterable[UnifiedMarket]) -> list[ArbitrageRow]:
        rows: list[ArbitrageRow] = []
        ts = datetime.now(timezone.utc).isoformat()
        for um in markets:
            rows.extend(self._scan_market(um, ts))
        rows.sort(key=lambda r: r.arbitrage_yield_percentage, reverse=True)
        return rows

    def _scan_market(self, um: UnifiedMarket, ts: str) -> list[ArbitrageRow]:
        out: list[ArbitrageRow] = []
        platform_legs = list(um.legs_by_platform.items())
        if len(platform_legs) < 2:
            return out

        for (p_a, legs_a), (p_b, legs_b) in combinations(platform_legs, 2):
            for la in legs_a:
                for lb in legs_b:
                    if match_outcome_names(la.outcome_key, lb.outcome_key):
                        continue
                    if um.market_type in ("spreads", "totals"):
                        if la.line is not None and lb.line is not None:
                            if abs(abs(la.line) - abs(lb.line)) > 0.01:
                                continue
                    result = two_way_arb_yield(float(la.american_odds), float(lb.american_odds))
                    if result is None:
                        continue
                    yield_pct, gap = result
                    if yield_pct < self.min_yield_pct:
                        continue
                    out.append(
                        ArbitrageRow(
                            timestamp=ts,
                            normalized_event_name=um.normalized_event_name,
                            market_type=um.market_type,
                            source_platform_a=p_a,
                            source_platform_b=p_b,
                            source_platform_a_odds=float(la.american_odds),
                            source_platform_b_odds=float(lb.american_odds),
                            implied_probability_gap=gap,
                            arbitrage_yield_percentage=yield_pct,
                            outcome_a=la.outcome_key,
                            outcome_b=lb.outcome_key,
                            line=la.line,
                        )
                    )
        return out

    def to_json(self, rows: list[ArbitrageRow]) -> dict:
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "count": len(rows),
            "opportunities": [r.to_dict() for r in rows],
        }
