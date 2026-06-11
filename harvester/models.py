"""Unified records shared by integrators and the arbitrage engine."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class SourceQuote(BaseModel):
    """One price line from a bookmaker for an outcome."""

    source: str
    outcome: str
    price: float
    line: float | None = None
    raw_label: str | None = None


class ArbitrageLeg(BaseModel):
    source: str
    outcome: str
    price: float
    stake_weight: float


class ArbitrageInfo(BaseModel):
    """Two-way (or n-way) arbitrage summary for a market."""

    yield_pct: float
    implied_sum: float
    legs: list[ArbitrageLeg] = Field(default_factory=list)


class UnifiedRecord(BaseModel):
    """
    Canonical wire format for merged odds + optional arb.

    Matches the architect schema:
    timestamp, normalized_event_name, market_type, sources, arbitrage.
    """

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    event_id: str
    sport_key: str
    normalized_event_name: str
    market_type: str
    commence_time: datetime | None = None
    sources: dict[str, list[SourceQuote]] = Field(default_factory=dict)
    arbitrage: ArbitrageInfo | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_export_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
