"""
Master ingestion loop — concurrent lawful adapters + merge + arb math.

Usage:
  python arbitrage_orchestrator.py
  python arbitrage_orchestrator.py --sport basketball_nba --out data/snapshot.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from engine import score_arbitrage
from fuzzy_normalizer import build_canonical_reference, map_entities_to_canonical
from integrator_factory import IntegratorFactory
from llm_arbitrage import filter_records_to_target_sources
from models import UnifiedRecord
from models_depth import IngestionSnapshot
from odds_api_fetch import (
  bulk_market_list,
  discover_and_resolve_sport_keys,
  fetch_odds_api_all_sports,
  fetch_sport_odds,
  resolve_sport_keys,
)
from settings import get_settings
from snapshot_builder import build_snapshot
from source_status import build_source_report

logger = logging.getLogger(__name__)


async def run_ingestion(
  sport_key: str | None = None,
  *,
  fast: bool = True,
  markets: list[str] | None = None,
) -> tuple[list[UnifiedRecord], IngestionSnapshot]:
  settings = get_settings()
  market_list = markets or bulk_market_list(settings)

  factory = IntegratorFactory()
  errors: list[str] = []

  try:
    if sport_key:
      sport_keys = [sport_key]
    elif settings.odds_api_sports.strip():
      sport_keys = resolve_sport_keys(settings)
    elif (settings.odds_api_sports_mode or "").strip().lower() in {"all_active", "all"}:
      sport_keys = await discover_and_resolve_sport_keys(factory)
    else:
      sport_keys = [settings.default_sport_key]

    if len(sport_keys) == 1:
      records = await fetch_sport_odds(factory, sport_keys[0])
    else:
      records = await fetch_odds_api_all_sports(factory, sport_keys, market_list)

    records = filter_records_to_target_sources(records)

    for src in factory.direct_only_sources():
      errors.append(f"{src.key}: requires official API — {src.integration_note}")

    if not fast and settings.use_local_normalization:
      fragments: list[str] = []
      for r in records:
        fragments.extend([r.metadata.get("home_team", ""), r.metadata.get("away_team", "")])
      fragments = [f for f in fragments if f]
      if fragments:
        ref = build_canonical_reference(*fragments)
        try:
          await map_entities_to_canonical(fragments, ref)
        except Exception as exc:
          errors.append(f"normalization: {exc}")

    records = await score_arbitrage(records, use_llm=False if fast else None)

    report = build_source_report(records)
    status_map = {row["key"]: row["status_label"] for row in report}

    snapshot_sport = sport_keys[0] if len(sport_keys) == 1 else "multi"
    snapshot = build_snapshot(records, sport_key=snapshot_sport, source_status=status_map, errors=errors)
    return records, snapshot
  finally:
    await factory.close()


async def main_async(args: argparse.Namespace) -> int:
  records, snapshot = await run_ingestion(args.sport, fast=not args.full, markets=args.markets)

  out_path = Path(args.output)
  out_path.parent.mkdir(parents=True, exist_ok=True)
  out_path.write_text(snapshot.model_dump_json(indent=2), encoding="utf-8")

  arb_count = sum(1 for r in records if r.arbitrage)
  print(
    json.dumps(
      {
        "events": len(snapshot.events),
        "lines": sum(len(e.lines) for e in snapshot.events),
        "arbitrage_records": arb_count,
        "output": str(out_path),
        "errors": snapshot.errors,
      },
      indent=2,
    )
  )
  return 0


def main() -> None:
  logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
  parser = argparse.ArgumentParser(description="Lawful multi-source ingestion orchestrator")
  parser.add_argument("--sport", default=None)
  parser.add_argument("--output", default="data/ingestion_snapshot.json")
  parser.add_argument("--full", action="store_true", help="Enable Ollama normalization/LLM (slow)")
  parser.add_argument("--markets", nargs="*", default=None, help="e.g. h2h spreads totals")
  args = parser.parse_args()
  raise SystemExit(asyncio.run(main_async(args)))


if __name__ == "__main__":
  main()
