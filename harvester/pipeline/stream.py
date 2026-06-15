"""
Emit minified JSON lines: timestamp, normalized_event_name, market_type,
sources, volume_depth, numerical_yield_delta.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Iterator

from engine import best_prices_implied_sum
from models_depth import EventSnapshot, MarketKind


def _yield_delta(implied_sum: float | None) -> float:
  if implied_sum is None or implied_sum <= 0:
    return 0.0
  if implied_sum < 1.0:
    return round((1.0 / implied_sum - 1.0) * 100.0, 4)
  return 0.0


def _volume_depth(event: EventSnapshot) -> float:
  total = 0.0
  for line in event.lines:
    for lvl in line.order_book:
      total += float(lvl.bid_size or 0) + float(lvl.ask_size or 0)
    for lvl in line.exchange_levels:
      total += float(lvl.back_volume or 0) + float(lvl.lay_volume or 0)
  return total


def yield_differential_records(
  events: list[EventSnapshot],
) -> Iterator[dict[str, Any]]:
  for ev in events:
    by_kind: dict[str, list] = {}
    for line in ev.lines:
      by_kind.setdefault(line.market_kind.value, []).append(line)

    for kind, lines in by_kind.items():
      sources = sorted({ln.source_key for ln in lines})
      source_a = sources[0] if sources else ""
      source_b = sources[1] if len(sources) > 1 else ""

      from models import UnifiedRecord, SourceQuote

      fake_sources: dict[str, list[SourceQuote]] = {}
      for ln in lines:
        fake_sources.setdefault(ln.source_key, []).append(
          SourceQuote(
            source=ln.source_key,
            outcome=ln.selection_name,
            price=ln.current_price_decimal,
            line=ln.line_value,
          )
        )

      rec = UnifiedRecord(
        event_id=ev.event_id,
        sport_key=ev.sport_key,
        normalized_event_name=ev.normalized_event_name,
        market_type=kind,
        commence_time=ev.commence_time,
        sources=fake_sources,
      )
      implied, _, _ = best_prices_implied_sum(rec)

      yield {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "normalized_event_name": ev.normalized_event_name,
        "market_type": kind,
        "source_A": source_a,
        "source_B": source_b,
        "volume_depth": _volume_depth(ev),
        "numerical_yield_delta": _yield_delta(implied),
        "line_count": len(lines),
      }


def stream_json_lines(events: list[EventSnapshot]) -> str:
  return "\n".join(json.dumps(row, separators=(",", ":")) for row in yield_differential_records(events))
