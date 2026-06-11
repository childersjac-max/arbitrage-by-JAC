"""Dashboard data: run pipeline, filter by day, compute summary stats."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any

from arb_line_engine import combinations_for_line_record
from engine import HarvesterEngine
from harvester_paths import PACKAGE_DIR
from models import ArbitrageLeg, UnifiedRecord
from settings import get_settings
from source_status import build_source_report, source_summary
from target_sources import ODDS_API_KEY_TO_TARGET, TARGET_SOURCE_BY_KEY
from time_utils import get_tz, today_and_tomorrow, to_local_date

logger = logging.getLogger(__name__)

CACHE_PATH = PACKAGE_DIR / "data" / "last_dashboard_run.json"


@dataclass
class RunState:
    running: bool = False
    run_status: str = ""
    last_error: str | None = None
    last_run_at: datetime | None = None
    run_started_at: datetime | None = None
    run_generation: int = 0
    records: list[UnifiedRecord] = field(default_factory=list)
    source_report: list[dict[str, Any]] = field(default_factory=list)


_state = RunState()
_active_run_task: asyncio.Task[None] | None = None


def reset_run_state() -> None:
    """Clear stuck 'running' flag (e.g. after server crash)."""
    global _active_run_task
    if _active_run_task is not None and not _active_run_task.done():
        _active_run_task.cancel()
    _active_run_task = None
    _state.running = False
    _state.run_status = ""
    _state.run_started_at = None


def maybe_reset_stale_run() -> None:
    """Auto-clear runs that exceeded the timeout (orphaned background tasks)."""
    if not _state.running or _state.run_started_at is None:
        return
    settings = get_settings()
    elapsed = (datetime.now(timezone.utc) - _state.run_started_at).total_seconds()
    if elapsed <= settings.run_timeout_sec + 30:
        return
    logger.warning("Stale dashboard run detected after %.0fs — resetting", elapsed)
    reset_run_state()
    _state.last_error = (
        f"Scan timed out after {int(settings.run_timeout_sec)}s. "
        "Showing last saved results. For faster refreshes keep "
        "HARVESTER_DASHBOARD_FAST_MODE=true (bulk markets only)."
    )


def get_run_state() -> RunState:
    return _state


def _local_tz() -> Any:
    return get_tz(get_settings().dashboard_timezone)


def _event_local_date(record: UnifiedRecord, tz: Any) -> date | None:
    if record.commence_time is None:
        return None
    return to_local_date(record.commence_time, tz)


def _sanitize_record_dict(item: dict[str, Any]) -> dict[str, Any]:
    """Fix legacy cache rows missing arbitrage.implied_sum."""
    arb = item.get("arbitrage")
    if isinstance(arb, dict) and arb:
        if "implied_sum" not in arb:
            legs = arb.get("legs") or []
            if legs and arb.get("yield_pct"):
                arb["implied_sum"] = 0.99
            else:
                item["arbitrage"] = None
        elif not arb.get("legs") and not arb.get("yield_pct"):
            item["arbitrage"] = None
    return item


_SPORT_LEAGUE_LABELS: dict[str, str] = {
    "basketball_nba": "NBA",
    "basketball_ncaab": "NCAAB",
    "basketball_wnba": "WNBA",
    "baseball_mlb": "MLB",
    "americanfootball_nfl": "NFL",
    "americanfootball_ncaaf": "NCAAF",
    "icehockey_nhl": "NHL",
    "mma_mixed_martial_arts": "MMA",
    "soccer_epl": "EPL",
    "soccer_usa_mls": "MLS",
}

_MARKET_LABELS: dict[str, str] = {
    "h2h": "Moneyline",
    "spreads": "Spreads",
    "totals": "Totals",
    "outrights": "Outrights",
}


def _decimal_to_american(price: float) -> int:
    if price <= 1.0:
        return 0
    if price >= 2.0:
        return int(round((price - 1.0) * 100))
    return int(round(-100 / (price - 1.0)))


def _humanize_market_type(market_type: str) -> str:
    key = (market_type or "").strip().lower()
    if key in _MARKET_LABELS:
        return _MARKET_LABELS[key]
    return key.replace("_", " ").title() if key else "Market"


def _sport_group(sport_key: str) -> str:
    prefix = (sport_key or "").split("_", 1)[0]
    return {
        "basketball": "Basketball",
        "baseball": "Baseball",
        "americanfootball": "Football",
        "icehockey": "Hockey",
        "soccer": "Soccer",
        "mma": "MMA",
        "tennis": "Tennis",
        "golf": "Golf",
        "boxing": "Boxing",
    }.get(prefix, prefix.replace("_", " ").title() if prefix else "Other")


def _sport_label(sport_key: str) -> str:
    if sport_key in _SPORT_LEAGUE_LABELS:
        return _SPORT_LEAGUE_LABELS[sport_key]
    parts = (sport_key or "").split("_")
    if len(parts) >= 2:
        return parts[-1].upper()
    return sport_key or "Sport"


def _canonical_source_key(book_key: str) -> str:
    return ODDS_API_KEY_TO_TARGET.get(book_key, book_key)


def _source_display(book_key: str) -> str:
    canonical = _canonical_source_key(book_key)
    target = TARGET_SOURCE_BY_KEY.get(canonical)
    if target:
        return target.name
    return canonical.replace("_", " ").title()


def _record_line(record: UnifiedRecord) -> float | None:
    meta_line = record.metadata.get("line")
    if meta_line is not None:
        try:
            return float(meta_line)
        except (TypeError, ValueError):
            pass
    for quotes in record.sources.values():
        for quote in quotes:
            if quote.line is not None:
                return quote.line
    return None


def _quote_line_for_outcome(record: UnifiedRecord, outcome: str) -> float | None:
    for quotes in record.sources.values():
        for quote in quotes:
            if quote.outcome == outcome and quote.line is not None:
                return quote.line
    return None


def _build_quote_matrix(record: UnifiedRecord) -> dict[str, Any]:
    outcomes: list[str] = []
    seen_outcomes: set[str] = set()
    books: list[str] = []
    seen_books: set[str] = set()
    prices: dict[str, dict[str, float]] = {}
    sums: dict[str, float] = {}
    counts: dict[str, int] = {}

    for book_key, quotes in record.sources.items():
        canonical = _canonical_source_key(book_key)
        if canonical not in seen_books:
            seen_books.add(canonical)
            books.append(canonical)
        for quote in quotes:
            if quote.price <= 1.0:
                continue
            outcome = quote.outcome
            if outcome not in seen_outcomes:
                seen_outcomes.add(outcome)
                outcomes.append(outcome)
            prices.setdefault(outcome, {})[canonical] = round(quote.price, 4)
            sums[outcome] = sums.get(outcome, 0.0) + quote.price
            counts[outcome] = counts.get(outcome, 0) + 1

    market_avg: dict[str, float] = {}
    for outcome, total in sums.items():
        n = counts.get(outcome, 0)
        if n:
            market_avg[outcome] = round(total / n, 4)

    return {
        "outcomes": outcomes,
        "books": books,
        "prices": prices,
        "market_avg": market_avg,
    }


def _enrich_leg(record: UnifiedRecord, leg: ArbitrageLeg, *, quote_matrix: dict[str, Any], bet_first: bool) -> dict[str, Any]:
    outcome = leg.outcome
    market_avg_price = quote_matrix.get("market_avg", {}).get(outcome)
    line = _quote_line_for_outcome(record, outcome)
    return {
        "source": _canonical_source_key(leg.source),
        "source_display": _source_display(leg.source),
        "outcome": outcome,
        "line": line,
        "price": leg.price,
        "american": _decimal_to_american(leg.price),
        "market_avg_price": market_avg_price,
        "market_avg_american": _decimal_to_american(market_avg_price) if market_avg_price else None,
        "stake_weight": leg.stake_weight,
        "is_bet_first": bet_first,
    }


def _build_filter_options(records: list[UnifiedRecord]) -> dict[str, Any]:
    sportsbook_counts: dict[str, int] = {}
    league_counts: dict[str, int] = {}
    market_counts: dict[str, int] = {}

    for record in records:
        market_counts[record.market_type] = market_counts.get(record.market_type, 0) + 1
        league_counts[record.sport_key] = league_counts.get(record.sport_key, 0) + 1
        for book_key in record.sources:
            canonical = _canonical_source_key(book_key)
            sportsbook_counts[canonical] = sportsbook_counts.get(canonical, 0) + 1

    sportsbooks = [
        {"key": key, "name": _source_display(key), "count": count}
        for key, count in sorted(sportsbook_counts.items(), key=lambda item: (-item[1], item[0]))
    ]
    sports_leagues = [
        {
            "key": key,
            "name": _sport_label(key),
            "group": _sport_group(key),
            "count": count,
        }
        for key, count in sorted(league_counts.items(), key=lambda item: (-item[1], item[0]))
    ]
    market_types = [
        {"key": key, "label": _humanize_market_type(key), "count": count}
        for key, count in sorted(market_counts.items(), key=lambda item: (-item[1], item[0]))
    ]

    return {
        "sportsbooks": sportsbooks,
        "sports_leagues": sports_leagues,
        "market_types": market_types,
    }


def _opportunity_from_record(record: UnifiedRecord) -> dict[str, Any] | None:
    arb = record.arbitrage
    if arb is None:
        return None
    settings = get_settings()
    if arb.yield_pct < settings.min_arb_yield_pct:
        return None

    quote_matrix = _build_quote_matrix(record)
    min_weight = min(leg.stake_weight for leg in arb.legs) if arb.legs else 0.0
    legs = [
        _enrich_leg(
            record,
            leg,
            quote_matrix=quote_matrix,
            bet_first=leg.stake_weight <= min_weight + 1e-9,
        )
        for leg in arb.legs
    ]
    roi_pct = float(arb.yield_pct)
    profit_usd_at_1000 = round(1000.0 * roi_pct / 100.0, 2)

    return {
        "id": record.event_id,
        "event_name": record.normalized_event_name,
        "sport_key": record.sport_key,
        "sport_group": _sport_group(record.sport_key),
        "sport_label": _sport_label(record.sport_key),
        "market_type": record.market_type,
        "market_label": _humanize_market_type(record.market_type),
        "line": _record_line(record),
        "commence_time": record.commence_time.isoformat() if record.commence_time else None,
        "yield_pct": arb.yield_pct,
        "roi_pct": roi_pct,
        "implied_sum": arb.implied_sum,
        "profit_usd_at_1000": profit_usd_at_1000,
        "legs": legs,
        "quote_matrix": quote_matrix,
        "arb_method": record.metadata.get("arb_method", "math"),
        "llm_reasoning": record.metadata.get("llm_reasoning", ""),
        "sources_used": record.metadata.get("sources_used", []),
    }


def _filter_records_by_day(records: list[UnifiedRecord], *, day: str) -> list[UnifiedRecord]:
    tz = _local_tz()
    today, tomorrow = today_and_tomorrow(tz)
    target = today if day == "today" else tomorrow
    out: list[UnifiedRecord] = []
    for record in records:
        event_date = _event_local_date(record, tz)
        if event_date == target:
            out.append(record)
        elif event_date is None and day == "today":
            out.append(record)
    return out


def _filter_by_day(
    opportunities: list[dict[str, Any]],
    records: list[UnifiedRecord],
    *,
    day: str,
) -> list[dict[str, Any]]:
    allowed = {r.event_id for r in _filter_records_by_day(records, day=day)}
    return [o for o in opportunities if o.get("id") in allowed]


def _parent_event_id(record: UnifiedRecord) -> str:
    return str(record.metadata.get("api_event_id") or record.event_id.split(":")[0])


def _count_parent_events(records: list[UnifiedRecord], *, day: str) -> int:
    tz = _local_tz()
    today, tomorrow = today_and_tomorrow(tz)
    target = today if day == "today" else tomorrow
    ids: set[str] = set()
    for record in records:
        event_date = _event_local_date(record, tz)
        if event_date == target:
            ids.add(_parent_event_id(record))
        elif event_date is None and day == "today":
            ids.add(_parent_event_id(record))
    return len(ids)


def _compute_scan_stats(records: list[UnifiedRecord]) -> dict[str, Any]:
    combinations = sum(combinations_for_line_record(r) for r in records)
    leagues = {r.sport_key for r in records if r.sport_key}
    events = {_parent_event_id(r) for r in records}
    market_types = {r.market_type for r in records if r.market_type}
    quotes = sum(len(qs) for r in records for qs in r.sources.values())
    return {
        "combinations_considered": combinations,
        "leagues_scanned": len(leagues),
        "quote_lines": len(records),
        "market_types_scanned": len(market_types),
        "quotes_total": quotes,
        "events_scanned": len(events),
        "sport_keys": sorted(leagues),
    }


def _compute_stats(opportunities: list[dict[str, Any]]) -> dict[str, Any]:
    if not opportunities:
        return {
            "total_opportunities": 0,
            "avg_profit_pct": 0.0,
            "best_available_pct": 0.0,
        }
    yields = [float(o["yield_pct"]) for o in opportunities]
    return {
        "total_opportunities": len(opportunities),
        "avg_profit_pct": round(sum(yields) / len(yields), 2),
        "best_available_pct": round(max(yields), 2),
    }


def build_dashboard_payload(
    records: list[UnifiedRecord],
    *,
    day: str = "today",
) -> dict[str, Any]:
    try:
        all_opps: list[dict[str, Any]] = []
        for record in records:
            opp = _opportunity_from_record(record)
            if opp:
                all_opps.append(opp)

        today_opps = _filter_by_day(all_opps, records, day="today")
        tomorrow_opps = _filter_by_day(all_opps, records, day="tomorrow")
        active = today_opps if day == "today" else tomorrow_opps

        events_today = _count_parent_events(records, day="today")
        events_tomorrow = _count_parent_events(records, day="tomorrow")

        sources = _state.source_report or build_source_report(records)
        loaded_sources = source_summary(sources).get("loaded", 0)

        best_edge = 0.0
        for opp in active:
            best_edge = max(best_edge, float(opp.get("yield_pct") or 0))

        scan_stats = _compute_scan_stats(records)

        run_summary = {
            "events_total": scan_stats["events_scanned"],
            "lines_total": len(records),
            "events_today": events_today,
            "events_tomorrow": events_tomorrow,
            "arbs_today": len(today_opps),
            "arbs_tomorrow": len(tomorrow_opps),
            "sources_loaded": loaded_sources,
            "best_edge_pct": round(best_edge, 2),
            "scan_stats": scan_stats,
        }

        return {
            "day": day,
            "stats": _compute_stats(active),
            "counts": {
                "today": len(today_opps),
                "tomorrow": len(tomorrow_opps),
            },
            "opportunities": active,
            "run_summary": run_summary,
            "sources": sources,
            "source_summary": source_summary(sources),
            "filter_options": _build_filter_options(records),
            "defaults": {"wager_usd": 1000, "sort_by": "roi_pct"},
            "last_run_at": _state.last_run_at.isoformat() if _state.last_run_at else None,
            "running": _state.running,
            "run_status": _state.run_status,
            "error": _state.last_error,
        }
    except Exception as exc:
        logger.exception("build_dashboard_payload failed")
        return {
            "day": day,
            "stats": _compute_stats([]),
            "counts": {"today": 0, "tomorrow": 0},
            "opportunities": [],
            "sources": _state.source_report or [],
            "source_summary": source_summary(_state.source_report or []),
            "last_run_at": _state.last_run_at.isoformat() if _state.last_run_at else None,
            "running": False,
            "run_status": "",
            "error": f"Dashboard error: {exc}",
        }


def _persist_cache(records: list[UnifiedRecord]) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "last_run_at": _state.last_run_at.isoformat() if _state.last_run_at else None,
        "records": [r.to_export_dict() for r in records],
        "source_report": _state.source_report,
    }
    CACHE_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_cached_records() -> list[UnifiedRecord]:
    if not CACHE_PATH.is_file():
        return []
    try:
        data = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        raw = data.get("records") or []
        records: list[UnifiedRecord] = []
        for item in raw:
            records.append(UnifiedRecord.model_validate(_sanitize_record_dict(item)))
        if data.get("last_run_at"):
            _state.last_run_at = datetime.fromisoformat(str(data["last_run_at"]))
        _state.source_report = list(data.get("source_report") or [])
        if not _state.source_report and records:
            _state.source_report = build_source_report(records)
        return records
    except Exception as exc:
        logger.warning("Could not load cache: %s", exc)
        return []


async def _run_pipeline(sport_key: str | None, *, generation: int) -> None:
    settings = get_settings()
    fast = settings.dashboard_fast_mode
    _state.run_status = (
        "Fetching odds (fast mode, bulk markets)…"
        if fast
        else "Fetching odds from The Odds API…"
    )
    engine = HarvesterEngine()
    records = await engine.run(sport_key, arbs_only=False, fast=fast)
    if generation != _state.run_generation:
        logger.info("Ignoring stale run results (generation %s)", generation)
        return
    _state.run_status = "Saving results…"
    _state.records = records
    _state.source_report = build_source_report(records)
    _state.last_run_at = datetime.now(timezone.utc)
    _persist_cache(records)
    _state.run_status = "Done"


async def execute_run(*, sport_key: str | None = None) -> None:
    if _state.running:
        return
    settings = get_settings()
    _state.run_generation += 1
    generation = _state.run_generation
    _state.running = True
    _state.last_error = None
    _state.run_started_at = datetime.now(timezone.utc)
    _state.run_status = "Starting…"
    try:
        if settings.dashboard_fast_mode:
            _state.run_status = "Fast scan (bulk markets + per-line arb)…"
        else:
            hint = ""
            if settings.use_llm_arbitrage or settings.use_local_normalization:
                hint = " (Ollama may take several minutes)"
            _state.run_status = f"Full pipeline{hint}…"
        await asyncio.wait_for(
            _run_pipeline(sport_key, generation=generation),
            timeout=settings.run_timeout_sec,
        )
    except asyncio.TimeoutError:
        logger.error("Dashboard run timed out after %ss", settings.run_timeout_sec)
        _state.run_generation += 1
        _state.last_error = (
            f"Timed out after {int(settings.run_timeout_sec)}s. "
            "Showing last saved results. For faster scans use "
            "HARVESTER_DASHBOARD_FAST_MODE=true or lower ODDS_API_MAX_SPORTS_PER_RUN."
        )
        if _state.records:
            _state.source_report = build_source_report(_state.records, api_error=_state.last_error)
        else:
            _state.source_report = build_source_report([], api_error=_state.last_error)
    except asyncio.CancelledError:
        logger.info("Dashboard run cancelled")
        _state.run_generation += 1
        _state.last_error = "Scan cancelled."
        raise
    except Exception as exc:
        logger.exception("Dashboard run failed")
        _state.run_generation += 1
        _state.last_error = str(exc)
        if _state.records:
            _state.source_report = build_source_report(_state.records, api_error=str(exc))
        else:
            _state.records = []
            _state.source_report = build_source_report([], api_error=str(exc))
            _persist_cache([])
    finally:
        _state.running = False
        _state.run_status = ""
        _state.run_started_at = None


async def execute_run_tracked(*, sport_key: str | None = None) -> None:
    """Wrapper used by the web app so background tasks can be cancelled."""
    global _active_run_task
    try:
        await execute_run(sport_key=sport_key)
    finally:
        _active_run_task = None
