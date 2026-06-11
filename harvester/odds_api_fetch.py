"""Multi-market and multi-sport Odds API fetch helpers."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from integrator_factory import IntegratorFactory
from models import UnifiedRecord
from settings import HarvesterSettings, get_settings

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
            logger.warning("Odds API market %s/%s failed: %s", sport_key, market, exc)
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


def resolve_sport_keys(
    settings: HarvesterSettings,
    discovered: list[str] | None = None,
) -> list[str]:
    """Pick sport keys for a run from env mode, explicit list, or default."""
    explicit = [s.strip() for s in settings.odds_api_sports.split(",") if s.strip()]
    if explicit:
        return explicit[: settings.odds_api_max_sports_per_run]

    mode = (settings.odds_api_sports_mode or "single").strip().lower()
    if mode in {"all_active", "all"} and discovered:
        excluded = {
            s.strip()
            for s in settings.odds_api_sports_exclude.split(",")
            if s.strip()
        }
        keys = [key for key in discovered if key not in excluded]
        return keys[: settings.odds_api_max_sports_per_run]

    return [settings.default_sport_key]


def cap_records_per_sport(
    records: list[UnifiedRecord],
    max_events: int,
) -> list[UnifiedRecord]:
    """Keep only the earliest `max_events` distinct events per sport."""
    if max_events <= 0 or not records:
        return records

    by_event: dict[str, UnifiedRecord] = {}
    for rec in records:
        by_event[rec.event_id] = rec

    min_dt = datetime.min.replace(tzinfo=timezone.utc)
    sorted_events = sorted(
        by_event.values(),
        key=lambda r: r.commence_time or min_dt,
    )
    allowed = {r.event_id for r in sorted_events[:max_events]}
    return [r for r in records if r.event_id in allowed]


async def fetch_odds_api_all_sports(
    factory: IntegratorFactory,
    sport_keys: list[str],
    markets: list[str],
    *,
    max_events_per_sport: int | None = None,
) -> list[UnifiedRecord]:
    """Fetch featured markets for every sport key and merge into one record list."""
    settings = get_settings()
    cap = max_events_per_sport
    if cap is None:
        cap = settings.odds_api_max_events_per_sport

    all_records: list[UnifiedRecord] = []
    for sport_key in sport_keys:
        try:
            batch = await fetch_odds_api_multi_market(factory, sport_key, markets)
            batch = cap_records_per_sport(batch, cap)
            all_records.extend(batch)
            logger.info(
                "Odds API %s: %s event(s), %s market(s)",
                sport_key,
                len({r.event_id for r in batch}),
                len(markets),
            )
        except Exception as exc:
            logger.warning("Odds API sport %s failed: %s", sport_key, exc)

    return all_records


async def discover_and_resolve_sport_keys(factory: IntegratorFactory) -> list[str]:
    """List active sports from the API and apply env caps/exclusions."""
    settings = get_settings()
    mode = (settings.odds_api_sports_mode or "single").strip().lower()
    if mode not in {"all_active", "all"} and not settings.odds_api_sports.strip():
        return [settings.default_sport_key]

    integrator = factory.odds_api_integrator()
    discovered = await integrator.list_active_sports(all_sports=mode == "all")
    keys = resolve_sport_keys(settings, discovered)
    logger.info("Resolved %s sport(s) for ingest: %s", len(keys), ", ".join(keys[:8]))
    if len(keys) > 8:
        logger.info("… and %s more", len(keys) - 8)
    return keys
