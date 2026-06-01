"""Build IngestionSnapshot from Odds API payloads and unified records."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from models import SourceQuote, UnifiedRecord
from models_depth import EventSnapshot, IngestionSnapshot, MarketKind, MarketLine
from target_sources import ODDS_API_KEY_TO_TARGET


def _kind_from_market_key(key: str) -> MarketKind:
  k = key.lower()
  if k in ("h2h", "moneyline", "head_to_head"):
    return MarketKind.MONEYLINE
  if k.startswith("spread") or k == "spreads":
    return MarketKind.SPREAD
  if k.startswith("total") or k == "totals":
    return MarketKind.TOTAL
  if "player" in k or k == "player_props":
    return MarketKind.PLAYER_PROP
  return MarketKind.MONEYLINE


def lines_from_unified_record(record: UnifiedRecord) -> list[MarketLine]:
  lines: list[MarketLine] = []
  ts = record.timestamp or datetime.now(timezone.utc)
  for book_key, quotes in record.sources.items():
    canonical = ODDS_API_KEY_TO_TARGET.get(book_key, book_key)
    for q in quotes:
      market_kind = _kind_from_market_key(record.market_type)
      lines.append(
        MarketLine(
          market_id=f"{record.event_id}:{canonical}:{record.market_type}:{q.outcome}:{q.line}",
          source_key=canonical,
          selection_name=q.outcome,
          market_kind=market_kind,
          current_price_decimal=q.price,
          line_value=q.line,
          is_live=bool(record.metadata.get("is_live")),
          last_timestamp=ts,
          metadata={"raw_book_key": book_key, "raw_label": q.raw_label},
        )
      )
  return lines


def merge_records_to_events(records: list[UnifiedRecord]) -> list[EventSnapshot]:
  """Merge multiple UnifiedRecords (one per market type) into one event."""
  by_event: dict[str, EventSnapshot] = {}
  for record in records:
    if record.event_id not in by_event:
      by_event[record.event_id] = EventSnapshot(
        event_id=record.event_id,
        sport_key=record.sport_key,
        normalized_event_name=record.normalized_event_name,
        commence_time=record.commence_time,
        home_team=str(record.metadata.get("home_team") or ""),
        away_team=str(record.metadata.get("away_team") or ""),
        lines=[],
      )
    by_event[record.event_id].lines.extend(lines_from_unified_record(record))
  return list(by_event.values())


def build_snapshot(
  records: list[UnifiedRecord],
  *,
  sport_key: str,
  source_status: dict[str, str] | None = None,
  errors: list[str] | None = None,
) -> IngestionSnapshot:
  return IngestionSnapshot(
    sport_key=sport_key,
    events=merge_records_to_events(records),
    source_status=source_status or {},
    errors=errors or [],
  )
