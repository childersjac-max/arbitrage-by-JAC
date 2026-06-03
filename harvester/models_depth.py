"""
Deep market schemas for multi-source arbitrage (Pydantic v2).

Designed for the full depth profile you specified. Fields for alternate
ladders, order-book levels, and exchange back/lay stacks are populated when
a lawful integrator supplies them (The Odds API, Kalshi API, Betfair API, etc.).
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class MarketKind(str, Enum):
    MONEYLINE = "moneyline"
    SPREAD = "spread"
    TOTAL = "total"
    PLAYER_PROP = "player_prop"
    BINARY_YES_NO = "binary_yes_no"
    EXCHANGE_BACK_LAY = "exchange_back_lay"


class OrderBookLevel(BaseModel):
  level: int = Field(ge=1, le=10)
  bid_price: float | None = None
  ask_price: float | None = None
  bid_size: float | None = None
  ask_size: float | None = None


class ExchangePriceLevel(BaseModel):
  level: int = Field(ge=1, le=3)
  back_price: float | None = None
  back_volume: float | None = None
  lay_price: float | None = None
  lay_volume: float | None = None


class MarketLine(BaseModel):
  """Single selectable line (sportsbook, contract, or exchange outcome)."""

  market_id: str
  source_key: str
  selection_name: str
  market_kind: MarketKind
  current_price_decimal: float
  line_value: float | None = None
  is_live: bool = False
  last_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
  alternate_ladder_index: int | None = None
  player_name: str | None = None
  prop_stat: str | None = None
  order_book: list[OrderBookLevel] = Field(default_factory=list)
  exchange_levels: list[ExchangePriceLevel] = Field(default_factory=list)
  metadata: dict[str, Any] = Field(default_factory=dict)


class EventSnapshot(BaseModel):
  event_id: str
  sport_key: str
  normalized_event_name: str
  commence_time: datetime | None = None
  home_team: str = ""
  away_team: str = ""
  lines: list[MarketLine] = Field(default_factory=list)


class IngestionSnapshot(BaseModel):
  """Unified real-time log payload from the orchestrator."""

  generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
  sport_key: str
  events: list[EventSnapshot] = Field(default_factory=list)
  source_status: dict[str, str] = Field(default_factory=dict)
  errors: list[str] = Field(default_factory=list)
