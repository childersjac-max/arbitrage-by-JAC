"""Merge integrator output, normalize entities, detect arbitrage (math + local LLM)."""

from __future__ import annotations

import logging

from config import get_settings
from integrators.odds_api import OddsApiIntegrator
from llm_arbitrage import analyze_arbitrage_with_llm, filter_records_to_target_sources
from models import ArbitrageInfo, ArbitrageLeg, SourceQuote, UnifiedRecord
from normalization.bridge import build_reference_from_names, normalize_team_labels

logger = logging.getLogger(__name__)


def detect_h2h_arbitrage(record: UnifiedRecord) -> ArbitrageInfo | None:
    """
    Find two-way arb using best decimal price per outcome across target sources.

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


def best_prices_implied_sum(record: UnifiedRecord) -> tuple[float | None, int, dict[str, tuple[float, str]]]:
    """
    Best decimal price per outcome across all books.
    Returns (implied_sum, outcome_count, best_by_outcome).
    """
    best_by_outcome: dict[str, tuple[float, str]] = {}
    for quotes in record.sources.values():
        for quote in quotes:
            if quote.price <= 1.0:
                continue
            current = best_by_outcome.get(quote.outcome)
            if current is None or quote.price > current[0]:
                best_by_outcome[quote.outcome] = (quote.price, quote.source)
    if len(best_by_outcome) < 2:
        return None, len(best_by_outcome), best_by_outcome
    implied_sum = sum(1.0 / price for price, _ in best_by_outcome.values())
    return implied_sum, len(best_by_outcome), best_by_outcome


def _merge_arbitrage(
    math_arb: ArbitrageInfo | None,
    llm_hit: dict | None,
    *,
    min_yield: float,
) -> ArbitrageInfo | None:
    """Prefer higher yield; combine metadata when both agree."""
    llm_arb = llm_hit.get("arbitrage") if llm_hit else None

    if math_arb and llm_arb:
        chosen = math_arb if math_arb.yield_pct >= llm_arb.yield_pct else llm_arb
        if chosen.yield_pct < min_yield:
            return None
        return chosen

    if math_arb and math_arb.yield_pct >= min_yield:
        return math_arb
    if llm_arb and llm_arb.yield_pct >= min_yield:
        return llm_arb
    return None


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


async def score_arbitrage(
    records: list[UnifiedRecord],
    *,
    use_llm: bool | None = None,
) -> list[UnifiedRecord]:
    """Math + optional local LLM arbitrage scoring across target sources."""
    settings = get_settings()
    min_yield = settings.min_arb_yield_pct
    llm_enabled = settings.use_llm_arbitrage if use_llm is None else use_llm

    llm_hits: dict[str, dict] = {}
    if llm_enabled:
        try:
            llm_hits = await analyze_arbitrage_with_llm(records)
        except Exception as exc:
            logger.warning("LLM arbitrage pass skipped: %s", exc)

    for record in records:
        math_arb = detect_h2h_arbitrage(record)
        llm_hit = llm_hits.get(record.event_id)
        merged = _merge_arbitrage(math_arb, llm_hit, min_yield=min_yield)

        if merged is not None:
            record.arbitrage = merged
            if math_arb and llm_hit:
                record.metadata["arb_method"] = "combined"
            elif llm_hit:
                record.metadata["arb_method"] = "llm"
            else:
                record.metadata["arb_method"] = "math"
            if llm_hit:
                record.metadata["llm_reasoning"] = llm_hit.get("reasoning", "")
                record.metadata["sources_used"] = llm_hit.get("sources_used", [])
        else:
            record.arbitrage = None
            record.metadata.pop("arb_method", None)

    return records


class HarvesterEngine:
    """End-to-end: fetch → target sources → normalize → LLM + math arbs."""

    async def run(
        self,
        sport_key: str | None = None,
        *,
        arbs_only: bool = False,
        fast: bool = False,
    ) -> list[UnifiedRecord]:
        settings = get_settings()
        sport = sport_key or settings.default_sport_key
        integrator = OddsApiIntegrator()
        try:
            records = await integrator.fetch_records(sport)
        finally:
            await integrator.close()

        records = filter_records_to_target_sources(records)

        if not fast and settings.use_local_normalization:
            records = await apply_normalization(records)

        records = await score_arbitrage(records, use_llm=False if fast else None)

        if arbs_only:
            return [
                r
                for r in records
                if r.arbitrage is not None and r.arbitrage.yield_pct >= settings.min_arb_yield_pct
            ]
        return records
