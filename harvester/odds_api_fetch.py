"""Multi-market, multi-sport, and per-event Odds API fetch helpers."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx

from integrator_factory import IntegratorFactory
from models import UnifiedRecord
from settings import HarvesterSettings, get_settings

logger = logging.getLogger(__name__)


def _report_fetch_progress(message: str) -> None:
    try:
        from dashboard_service import get_run_state

        get_run_state().run_status = message
    except Exception:
        pass

DEFAULT_EVENT_MARKETS = (
    "alternate_spreads,alternate_totals,alternate_team_totals,"
    "player_points,player_rebounds,player_assists,player_threes,"
    "player_points_alternate,player_rebounds_alternate,player_assists_alternate,"
    "player_pass_yds,player_rush_yds,player_receptions,player_anytime_td,"
    "batter_hits,pitcher_strikeouts,player_goals,player_shots_on_goal,"
    "btts,draw_no_bet"
)


def bulk_market_list(settings: HarvesterSettings | None = None) -> list[str]:
    settings = settings or get_settings()
    raw = settings.odds_api_bulk_markets or settings.odds_api_markets
    return [m.strip() for m in raw.split(",") if m.strip()]


def event_market_list(settings: HarvesterSettings | None = None) -> list[str]:
    settings = settings or get_settings()
    raw = settings.odds_api_event_markets or DEFAULT_EVENT_MARKETS
    return [m.strip() for m in raw.split(",") if m.strip()]


async def fetch_odds_api_multi_market(
    factory: IntegratorFactory,
    sport_key: str,
    markets: list[str],
) -> list[UnifiedRecord]:
    """Fetch each market type from The Odds API (each market uses API quota)."""
    integrator = factory.odds_api_integrator()
    all_records: list[UnifiedRecord] = []

    for market in markets:
        try:
            batch = await integrator.fetch_records(sport_key, market_types=[market])
            all_records.extend(batch)
        except Exception as exc:
            logger.warning("Odds API market %s/%s failed: %s", sport_key, market, exc)

    return all_records


async def fetch_deep_event_markets(
    factory: IntegratorFactory,
    sport_key: str,
    *,
    max_events: int | None = None,
) -> list[UnifiedRecord]:
    """Per-event odds for props and alternates (1 credit × market × event)."""
    settings = get_settings()
    if not settings.odds_api_deep_markets:
        return []

    cap = max_events if max_events is not None else settings.odds_api_max_events_per_sport
    markets = event_market_list(settings)
    if not markets:
        return []

    integrator = factory.odds_api_integrator()
    try:
        events = await integrator.list_events(sport_key)
    except Exception as exc:
        logger.warning("Odds API events list %s failed: %s", sport_key, exc)
        return []

    events = events[:cap] if cap > 0 else events
    records: list[UnifiedRecord] = []
    chunk_size = 8

    for event in events:
        event_id = str(event.get("id") or "")
        if not event_id:
            continue
        for idx in range(0, len(markets), chunk_size):
            chunk = markets[idx : idx + chunk_size]
            try:
                batch = await integrator.fetch_event_odds(sport_key, event_id, chunk)
                records.extend(batch)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 422:
                    continue
                logger.warning(
                    "Odds API event %s/%s markets %s: %s",
                    sport_key,
                    event_id,
                    chunk,
                    exc,
                )
            except Exception as exc:
                logger.warning(
                    "Odds API event %s/%s markets %s: %s",
                    sport_key,
                    event_id,
                    chunk,
                    exc,
                )

    logger.info(
        "Odds API deep %s: %s event(s), %s line record(s)",
        sport_key,
        len(events),
        len(records),
    )
    return records


async def fetch_sport_odds(
    factory: IntegratorFactory,
    sport_key: str,
    *,
    max_events_per_sport: int | None = None,
    fast: bool = False,
) -> list[UnifiedRecord]:
    """Bulk featured markets + optional per-event props/alternates for one sport."""
    settings = get_settings()
    if max_events_per_sport is None:
        cap = (
            settings.dashboard_max_events_per_sport
            if fast
            else settings.odds_api_max_events_per_sport
        )
    else:
        cap = max_events_per_sport

    _report_fetch_progress(f"Fetching {sport_key} (bulk markets)…")
    bulk = await fetch_odds_api_multi_market(factory, sport_key, bulk_market_list(settings))
    merged = list(bulk)
    if settings.odds_api_deep_markets and not fast:
        _report_fetch_progress(f"Fetching {sport_key} (props & alternates)…")
        deep = await fetch_deep_event_markets(factory, sport_key, max_events=cap)
        merged.extend(deep)
    return cap_records_per_sport(merged, cap)


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


def _parent_event_id(record: UnifiedRecord) -> str:
    return str(record.metadata.get("api_event_id") or record.event_id.split(":")[0])


def cap_records_per_sport(
    records: list[UnifiedRecord],
    max_events: int,
) -> list[UnifiedRecord]:
    """Keep only the earliest `max_events` distinct parent events per sport."""
    if max_events <= 0 or not records:
        return records

    by_event: dict[str, UnifiedRecord] = {}
    for rec in records:
        by_event[_parent_event_id(rec)] = rec

    min_dt = datetime.min.replace(tzinfo=timezone.utc)
    sorted_events = sorted(
        by_event.values(),
        key=lambda r: r.commence_time or min_dt,
    )
    allowed = {_parent_event_id(r) for r in sorted_events[:max_events]}
    return [r for r in records if _parent_event_id(r) in allowed]


async def fetch_odds_api_all_sports(
    factory: IntegratorFactory,
    sport_keys: list[str],
    markets: list[str] | None = None,
    *,
    max_events_per_sport: int | None = None,
    fast: bool = False,
) -> list[UnifiedRecord]:
    """Fetch bulk + deep markets for every sport key."""
    settings = get_settings()
    if max_events_per_sport is None:
        cap = (
            settings.dashboard_max_events_per_sport
            if fast
            else settings.odds_api_max_events_per_sport
        )
    else:
        cap = max_events_per_sport

    if fast:
        sport_keys = sport_keys[: settings.dashboard_max_sports_per_run]

    total = len(sport_keys)
    all_records: list[UnifiedRecord] = []
    for index, sport_key in enumerate(sport_keys, start=1):
        try:
            _report_fetch_progress(f"Fetching {sport_key} ({index}/{total})…")
            if settings.odds_api_deep_markets and not fast:
                batch = await fetch_sport_odds(
                    factory, sport_key, max_events_per_sport=cap, fast=fast
                )
            else:
                market_list = markets or bulk_market_list(settings)
                batch = await fetch_odds_api_multi_market(factory, sport_key, market_list)
                batch = cap_records_per_sport(batch, cap)
            all_records.extend(batch)
            logger.info(
                "Odds API %s: %s parent event(s), %s line record(s)",
                sport_key,
                len({_parent_event_id(r) for r in batch}),
                len(batch),
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
