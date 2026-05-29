"""Canonical in-memory models for splice + arbitrage output."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class OutcomeQuote:
    name: str
    price_american: int | float
    point: float | None = None
    implied_prob: float | None = None
    volume: float | None = None  # contracts/shares at best level when known


@dataclass
class MarketQuote:
    key: str
    outcomes: list[OutcomeQuote]
    last_update: str | None = None
    line: float | None = None


@dataclass
class SourceBook:
    """One book/exchange attached to an event."""

    source_id: str
    title: str
    markets: list[MarketQuote] = field(default_factory=list)
    raw: dict[str, Any] | None = None


@dataclass
class NormalizedEvent:
    event_id: str
    sport_key: str
    normalized_name: str
    home_team: str
    away_team: str
    commence_time: str
    books: list[SourceBook] = field(default_factory=list)

    def book_by_source(self, source_id: str) -> SourceBook | None:
        for b in self.books:
            if b.source_id == source_id:
                return b
        return None


@dataclass
class ArbitrageSignal:
    timestamp: str
    normalized_event_name: str
    market_type: str
    source_a_odds_and_volume: dict[str, Any]
    source_b_odds_and_volume: dict[str, Any]
    calculated_arbitrage_yield_percentage: float
    sport_key: str
    commence_time: str
    legs: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "normalized_event_name": self.normalized_event_name,
            "market_type": self.market_type,
            "source_A_odds_and_volume": self.source_a_odds_and_volume,
            "source_B_odds_and_volume": self.source_b_odds_and_volume,
            "calculated_arbitrage_yield_percentage": self.calculated_arbitrage_yield_percentage,
            "sport_key": self.sport_key,
            "commence_time": self.commence_time,
            "legs": self.legs,
        }


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )
