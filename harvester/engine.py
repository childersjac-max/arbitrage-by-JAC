"""Merge integrator output, normalize entities, detect arbitrage."""

from __future__ import annotations

import logging
from collections import defaultdict

from config import get_settings
from integrators.odds_api import OddsApiIntegrator
from models import ArbitrageInfo, ArbitrageLeg, SourceQuote, UnifiedRecord
from normalization.bridge import build_reference_from_names, normalize_team_labels

logger = logging.getLogger(__name__)


def detect_h2h_arbitrage(record: UnifiedRecord) -> ArbitrageInfo | None:
    """
    Find two-way arb using best decimal price per outcome across all books.

    Arb exists when sum(1/price_i) < 1 for the best prices on each side.
    """
    best_by_outcome: dict[str, tuple[float, str]] = {}

    for book_key, quotes in record.sources.items():
        for quote in quotes:
            if quote.price <= 1.0:
                continue
            current = best_by_outcome.get(quote.outcome)
            if current is None or quote.price > current[0]:
                best_by_outcome[quote.outcome] = (quote.price, book_key)

    if len(best_by_outcome) < 2:
        return None

    implied_sum = sum(1.0 / price for price, _ in best_by_outcome.values())
    if implied_sum >= 1.0:
        return None

    yield_pct = (1.0 / implied_sum - 1.0) * 100.0
    legs: list[ArbitrageLeg] = []
    for outcome, (price, book) in best_by_outcome.items():
        weight = (1.0 / price) / implied_sum
        legs.append(
            ArbitrageLeg(
                source=book,
                outcome=outcome,
                price=price,
                stake_weight=round(weight, 6),
            )
        )

    return ArbitrageInfo(yield_pct=round(yield_pct, 4), implied_sum=round(implied_sum, 6), legs=legs)


def _collect_name_fragments(records: list[UnifiedRecord]) -> list[str]:
    fragments: list[str] = []
    for record in records:
        meta = record.metadata
        for key in ("home_team", "away_team"):
            val = meta.get(key)
            if val:
                fragments.append(str(val))
        for quotes in record.sources.values():
            for q in quotes:
                if q.raw_label:
                    fragments.append(q.raw_label)
                elif q.outcome:
                    fragments.append(q.outcome)
    return fragments


async def apply_normalization(records: list[UnifiedRecord]) -> list[UnifiedRecord]:
    """Normalize team/outcome strings and refresh display names."""
    fragments = _collect_name_fragments(records)
    if not fragments:
        return records

    reference = build_reference_from_names(fragments)
    try:
        mapping = await normalize_team_labels(fragments, reference)
    except Exception as exc:
        logger.warning("Normalization skipped: %s", exc)
        return records

    for record in records:
        home = str(record.metadata.get("home_team") or "")
        away = str(record.metadata.get("away_team") or "")
        norm_home = mapping.get(home) or home
        norm_away = mapping.get(away) or away
        if norm_home and norm_away:
            record.normalized_event_name = f"{norm_away} @ {norm_home}"
        for quotes in record.sources.values():
            for q in quotes:
                if q.raw_label and q.raw_label in mapping and mapping[q.raw_label]:
                    q.outcome = str(mapping[q.raw_label])
    return records


class HarvesterEngine:
    """End-to-end pipeline: fetch → normalize → score arbs."""

    async def run(
        self,
        sport_key: str | None = None,
        *,
        arbs_only: bool = False,
    ) -> list[UnifiedRecord]:
        settings = get_settings()
        sport = sport_key or settings.default_sport_key
        integrator = OddsApiIntegrator()
        try:
            records = await integrator.fetch_records(sport)
        finally:
            await integrator.close()

        if settings.use_local_normalization:
            records = await apply_normalization(records)

        for record in records:
            record.arbitrage = detect_h2h_arbitrage(record)

        if arbs_only:
            min_yield = settings.min_arb_yield_pct
            return [
                r
                for r in records
                if r.arbitrage is not None and r.arbitrage.yield_pct >= min_yield
            ]
        return records
