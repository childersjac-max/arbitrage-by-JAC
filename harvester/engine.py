"""Merge integrator output, normalize entities, detect arbitrage (math + local LLM)."""

from __future__ import annotations

import logging

from arb_line_engine import detect_best_arb_for_record, expand_records_to_lines
from config import get_settings
from llm_arbitrage import analyze_arbitrage_with_llm, filter_records_to_target_sources
from models import ArbitrageInfo, ArbitrageLeg, SourceQuote, UnifiedRecord
from normalization.bridge import build_reference_from_names, normalize_team_labels

logger = logging.getLogger(__name__)


def best_prices_implied_sum(
    record: UnifiedRecord,
) -> tuple[float | None, int, dict[str, tuple[float, str]]]:
    """
    Best decimal price per outcome across all books on the record's primary line.
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
    """Per-line math arb (+ optional LLM) across all market types."""
    settings = get_settings()
    min_yield = settings.min_arb_yield_pct
    llm_enabled = settings.use_llm_arbitrage if use_llm is None else use_llm

    line_records = expand_records_to_lines(records)

    llm_hits: dict[str, dict] = {}
    if llm_enabled:
        try:
            llm_hits = await analyze_arbitrage_with_llm(line_records)
        except Exception as exc:
            logger.warning("LLM arbitrage pass skipped: %s", exc)

    for record in line_records:
        math_arb = detect_best_arb_for_record(record)
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

    return line_records


class HarvesterEngine:
    """End-to-end: fetch → target sources → normalize → per-line arb scoring."""

    async def run(
        self,
        sport_key: str | None = None,
        *,
        arbs_only: bool = False,
        fast: bool = False,
    ) -> list[UnifiedRecord]:
        settings = get_settings()
        from integrator_factory import IntegratorFactory
        from odds_api_fetch import (
            bulk_market_list,
            discover_and_resolve_sport_keys,
            fetch_odds_api_all_sports,
            fetch_sport_odds,
            resolve_sport_keys,
        )

        factory = IntegratorFactory()
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
                records = await fetch_sport_odds(factory, sport_keys[0], fast=fast)
            else:
                records = await fetch_odds_api_all_sports(
                    factory, sport_keys, bulk_market_list(), fast=fast
                )
        finally:
            await factory.close()

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
