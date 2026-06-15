"""Dashboard data: run pipeline, filter by day, compute summary stats."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any

from allocation.balances import balances_snapshot, get_book_balances, save_book_balances
from allocation.optimizer import enrich_opportunities, optimize_portfolio
from engine import HarvesterEngine, best_prices_implied_sum
from harvester_paths import PACKAGE_DIR
from models import UnifiedRecord
from settings import get_settings
from source_status import build_source_report, source_summary
from time_utils import get_tz, today_and_tomorrow, to_local_date

logger = logging.getLogger(__name__)

CACHE_PATH = PACKAGE_DIR / "data" / "last_dashboard_run.json"


@dataclass
class RunState:
    running: bool = False
    run_status: str = ""
    last_error: str | None = None
    last_run_at: datetime | None = None
    records: list[UnifiedRecord] = field(default_factory=list)
    source_report: list[dict[str, Any]] = field(default_factory=list)


def reset_run_state() -> None:
    """Clear stuck 'running' flag (e.g. after server crash)."""
    _state.running = False
    _state.run_status = ""


_state = RunState()


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


def _opportunity_from_record(record: UnifiedRecord) -> dict[str, Any] | None:
    arb = record.arbitrage
    if arb is None:
        return None
    settings = get_settings()
    if arb.yield_pct < settings.min_arb_yield_pct:
        return None
    legs = [
        {
            "source": leg.source,
            "outcome": leg.outcome,
            "price": leg.price,
            "stake_weight": leg.stake_weight,
        }
        for leg in arb.legs
    ]
    return {
        "id": record.event_id,
        "event_name": record.normalized_event_name,
        "sport_key": record.sport_key,
        "market_type": record.market_type,
        "commence_time": record.commence_time.isoformat() if record.commence_time else None,
        "yield_pct": arb.yield_pct,
        "implied_sum": arb.implied_sum,
        "legs": legs,
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


def _scanned_event_from_record(record: UnifiedRecord) -> dict[str, Any]:
    implied_sum, _, _ = best_prices_implied_sum(record)
    books = len(record.sources)
    yield_pct = 0.0
    has_arb = False
    if record.arbitrage is not None:
        has_arb = True
        yield_pct = record.arbitrage.yield_pct
    elif implied_sum is not None and implied_sum < 1.0:
        has_arb = True
        yield_pct = round((1.0 / implied_sum - 1.0) * 100.0, 4)

    overround_pct = round((implied_sum - 1.0) * 100.0, 2) if implied_sum and implied_sum >= 1.0 else None

    legs: list[dict[str, Any]] = []
    if record.arbitrage:
        legs = [
            {
                "source": leg.source,
                "outcome": leg.outcome,
                "price": leg.price,
                "stake_weight": leg.stake_weight,
            }
            for leg in record.arbitrage.legs
        ]

    return {
        "id": record.event_id,
        "event_name": record.normalized_event_name,
        "sport_key": record.sport_key,
        "market_type": record.market_type,
        "commence_time": record.commence_time.isoformat() if record.commence_time else None,
        "books_count": books,
        "has_arbitrage": has_arb,
        "yield_pct": yield_pct,
        "implied_sum": round(implied_sum, 4) if implied_sum is not None else None,
        "overround_pct": overround_pct,
        "is_opportunity": has_arb and yield_pct >= get_settings().min_arb_yield_pct,
        "legs": legs,
        "arb_method": record.metadata.get("arb_method", "math"),
        "llm_reasoning": record.metadata.get("llm_reasoning", ""),
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

        balances = get_book_balances()
        portfolio = optimize_portfolio(active, balances)
        active = enrich_opportunities(active, portfolio)

        today_events = [_scanned_event_from_record(r) for r in _filter_records_by_day(records, day="today")]
        tomorrow_events = [_scanned_event_from_record(r) for r in _filter_records_by_day(records, day="tomorrow")]
        active_events = today_events if day == "today" else tomorrow_events

        sources = _state.source_report or build_source_report(records)
        loaded_sources = source_summary(sources).get("loaded", 0)

        best_edge = 0.0
        for ev in active_events:
            if ev.get("has_arbitrage"):
                best_edge = max(best_edge, float(ev.get("yield_pct") or 0))

        run_summary = {
            "events_total": len(records),
            "events_today": len(today_events),
            "events_tomorrow": len(tomorrow_events),
            "arbs_today": len(today_opps),
            "arbs_tomorrow": len(tomorrow_opps),
            "sources_loaded": loaded_sources,
            "best_edge_pct": round(best_edge, 2),
        }

        return {
            "day": day,
            "stats": _compute_stats(active),
            "counts": {
                "today": len(today_events),
                "tomorrow": len(tomorrow_events),
            },
            "opportunities": active,
            "scanned_events": active_events,
            "portfolio": portfolio.to_dict(),
            "balances": balances_snapshot(),
            "run_summary": run_summary,
            "sources": sources,
            "source_summary": source_summary(sources),
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


async def _run_pipeline(sport_key: str | None) -> None:
    settings = get_settings()
    fast = settings.dashboard_fast_mode
    _state.run_status = (
        "Fetching odds (fast mode, no Ollama)…"
        if fast
        else "Fetching odds from The Odds API…"
    )
    engine = HarvesterEngine()
    records = await engine.run(sport_key, arbs_only=False, fast=fast)
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
    _state.running = True
    _state.last_error = None
    _state.run_status = "Starting…"
    try:
        if settings.dashboard_fast_mode:
            _state.run_status = "Fast scan (Odds API + math only)…"
        else:
            hint = ""
            if settings.use_llm_arbitrage or settings.use_local_normalization:
                hint = " (Ollama may take several minutes)"
            _state.run_status = f"Full pipeline{hint}…"
        await asyncio.wait_for(
            _run_pipeline(sport_key),
            timeout=settings.run_timeout_sec,
        )
    except asyncio.TimeoutError:
        logger.error("Dashboard run timed out after %ss", settings.run_timeout_sec)
        _state.last_error = (
            f"Timed out after {int(settings.run_timeout_sec)}s. "
            "Keep Ollama open, or set HARVESTER_USE_LLM_ARBITRAGE=false and "
            "HARVESTER_USE_LOCAL_NORMALIZATION=false in harvester/.env for a faster run."
        )
        _state.source_report = build_source_report(_state.records, api_error=_state.last_error)
    except Exception as exc:
        logger.exception("Dashboard run failed")
        _state.last_error = str(exc)
        _state.records = []
        _state.source_report = build_source_report([], api_error=str(exc))
        _persist_cache([])
    finally:
        _state.running = False
        if not _state.last_error:
            _state.run_status = ""
