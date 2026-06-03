"""Multi-market Odds API fetch helpers."""

from __future__ import annotations

import logging

from integrator_factory import IntegratorFactory
from models import UnifiedRecord

logger = logging.getLogger(__name__)


async def fetch_odds_api_multi_market(
  factory: IntegratorFactory,
  sport_key: str,
  markets: list[str],
) -> list[UnifiedRecord]:
  """Fetch each market type from The Odds API (each market uses API quota)."""
  integrator = factory.odds_api_integrator()
  merged: dict[str, UnifiedRecord] = {}

  for market in markets:
    try:
      batch = await integrator.fetch_records(sport_key, market_types=[market])
    except Exception as exc:
      logger.warning("Odds API market %s failed: %s", market, exc)
      continue
    for rec in batch:
      rec.market_type = market
      if rec.event_id not in merged:
        merged[rec.event_id] = rec
      else:
        existing = merged[rec.event_id]
        for book, quotes in rec.sources.items():
          existing.sources.setdefault(book, []).extend(quotes)

  return list(merged.values())
