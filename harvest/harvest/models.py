"""Canonical in-memory models before normalization."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class PlatformKind(str, Enum):
    SPORTSBOOK = "sportsbook"
    PREDICTION_MARKET = "prediction_market"
    EXCHANGE = "exchange"


class MarketType(str, Enum):
    MONEYLINE = "Moneyline"
    SPREAD = "Spread"
    TOTAL = "Total"
    PLAYER_PROP = "Player Prop"
    YES_NO = "Yes/No Contract"
    BACK_LAY = "Back/Lay"


@dataclass
class PriceQuote:
    platform: str
    outcome_label: str
    american_odds: int | None = None
    decimal_odds: float | None = None
    implied_prob: float | None = None
    liquidity_volume: float | None = None
    line: float | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    def effective_decimal(self) -> float | None:
        if self.decimal_odds and self.decimal_odds > 1:
            return self.decimal_odds
        if self.implied_prob and 0 < self.implied_prob < 1:
            return 1.0 / self.implied_prob
        if self.american_odds is None:
            return None
        a = self.american_odds
        if a >= 100:
            return a / 100.0 + 1.0
        if a <= -100:
            return 100.0 / abs(a) + 1.0
        return None


@dataclass
class MarketFragment:
    source: str
    platform_kind: PlatformKind
    sport: str
    league: str | None
    home_team: str
    away_team: str
    commence_time: str | None
    market_type: MarketType
    market_key: str
    quotes: list[PriceQuote]
    metadata: dict[str, Any] = field(default_factory=dict)
    fetched_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass
class UnifiedArbitrageRow:
    """Exact output schema requested by the arbitrage board."""

    timestamp: str
    normalized_event_name: str
    market_type: str
    source_A: dict[str, Any]
    source_B: dict[str, Any]
    arbitrage_yield_percentage: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "normalized_event_name": self.normalized_event_name,
            "market_type": self.market_type,
            "source_A": self.source_A,
            "source_B": self.source_B,
            "arbitrage_yield_percentage": self.arbitrage_yield_percentage,
        }
