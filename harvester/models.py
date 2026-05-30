"""Typed schemas for source quotes and unified arbitrage output."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""

    return datetime.now(timezone.utc)


class MarketType(str, Enum):
    """Canonical market types emitted by the harvester."""

    MONEYLINE = "moneyline"
    SPREAD = "spread"
    TOTAL = "total"
    BINARY_YES_NO = "binary_yes_no"
    OTHER = "other"


class SourceQuote(BaseModel):
    """One price observed from one source before normalization and merge."""

    model_config = ConfigDict(use_enum_values=True)

    source_id: str = Field(..., description="Stable source identifier.")
    sport: str
    raw_event_id: str | None = None
    raw_event_name: str
    start_time: datetime
    market_type: MarketType | str
    selection_name: str | None = None
    line: float | None = None
    odds: float | None = None
    volume: float | None = None
    liquidity: float | None = None
    url: str | None = None
    fetched_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SourceSnapshot(BaseModel):
    """Source payload embedded under the unified output `sources` map."""

    raw_event_name: str
    odds: float | None = None
    volume: float | None = None
    liquidity: float | None = None
    url: str | None = None
    fetched_at: datetime


class BestPrice(BaseModel):
    """Best back or lay price descriptor."""

    source: str
    price: float


class ArbitrageBlock(BaseModel):
    """Arbitrage summary for comparable prices."""

    best_back: BestPrice
    best_lay: BestPrice
    yield_pct: float


class UnifiedEvent(BaseModel):
    """Unified event/market payload emitted for each harvester tick.

    The fields requested by the app are preserved exactly. Additional
    `sport`, `start_time`, `selection_name`, and `line` fields make market
    comparability explicit for downstream consumers.
    """

    model_config = ConfigDict(use_enum_values=True)

    timestamp: datetime
    normalized_event_id: str
    normalized_event_name: str
    market_type: MarketType | str
    sport: str
    start_time: datetime
    selection_name: str | None = None
    line: float | None = None
    sources: dict[str, SourceSnapshot]
    arbitrage: ArbitrageBlock | None = None

    def to_jsonable(self, include_null_arbitrage: bool = False) -> dict[str, Any]:
        """Return a JSON-ready dict using ISO-8601 timestamps."""

        data = self.model_dump(mode="json")
        if not include_null_arbitrage and data.get("arbitrage") is None:
            data.pop("arbitrage", None)
        return data


class AdapterFetchResult(BaseModel):
    """Structured result returned by source adapters."""

    source_id: str
    quotes: list[SourceQuote] = Field(default_factory=list)
    fetched_at: datetime = Field(default_factory=utc_now)
    status: Literal["ok", "source_unavailable", "error"] = "ok"
    message: str | None = None
