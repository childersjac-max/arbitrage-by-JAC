"""Canonical data models for fragmented source packets and unified arb rows."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class OddsLeg:
    platform: str
    outcome_key: str
    american_odds: int | float
    line: float | None = None
    implied_prob: float | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class MarketPacket:
    """Fragment from any profile — may be partial until spliced."""

    source_platform: str
    event_key: str
    home_team: str
    away_team: str
    market_type: str
    commence_time: str | None
    legs: list[OddsLeg]
    fetched_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_complete_two_way(self) -> bool:
        return len(self.legs) >= 2


@dataclass
class UnifiedMarket:
    """Merged view after normalization + splice."""

    normalized_event_name: str
    market_type: str
    commence_time: str | None
    home_team: str
    away_team: str
    legs_by_platform: dict[str, list[OddsLeg]]
    event_key: str
    splice_sources: list[str] = field(default_factory=list)


@dataclass
class ArbitrageRow:
    """Output schema for downstream arb calculators."""

    timestamp: str
    normalized_event_name: str
    market_type: str
    source_platform_a: str
    source_platform_b: str
    source_platform_a_odds: float
    source_platform_b_odds: float
    implied_probability_gap: float
    arbitrage_yield_percentage: float
    outcome_a: str
    outcome_b: str
    line: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "normalized_event_name": self.normalized_event_name,
            "market_type": self.market_type,
            "source_platform_a_odds": self.source_platform_a_odds,
            "source_platform_b_odds": self.source_platform_b_odds,
            "source_platform_a": self.source_platform_a,
            "source_platform_b": self.source_platform_b,
            "implied_probability_gap": round(self.implied_probability_gap, 6),
            "arbitrage_yield_percentage": round(self.arbitrage_yield_percentage, 4),
            "outcome_a": self.outcome_a,
            "outcome_b": self.outcome_b,
            "line": self.line,
        }
