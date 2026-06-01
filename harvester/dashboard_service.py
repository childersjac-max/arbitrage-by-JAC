"""Dashboard data: run pipeline, filter by day, compute summary stats."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from config import get_settings
from engine import HarvesterEngine
from models import UnifiedRecord
from paths import PACKAGE_DIR

logger = logging.getLogger(__name__)

CACHE_PATH = PACKAGE_DIR / "data" / "last_dashboard_run.json"


@dataclass
class RunState:
    running: bool = False
    last_error: str | None = None
    last_run_at: datetime | None = None
    records: list[UnifiedRecord] = field(default_factory=list)


_state = RunState()


def get_run_state() -> RunState:
    return _state


def _local_tz() -> ZoneInfo:
    try:
        return ZoneInfo("America/New_York")
    except Exception:
        return ZoneInfo("UTC")


def _event_local_date(record: UnifiedRecord, tz: ZoneInfo) -> date | None:
    commence = record.commence_time
    if commence is None:
        return None
    if commence.tzinfo is None:
        commence = commence.replace(tzinfo=timezone.utc)
    return commence.astimezone(tz).date()


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
    }


def _filter_by_day(
    opportunities: list[dict[str, Any]],
    records: list[UnifiedRecord],
    *,
    day: str,
) -> list[dict[str, Any]]:
    tz = _local_tz()
    today = datetime.now(tz).date()
    tomorrow = today + timedelta(days=1)
    target = today if day == "today" else tomorrow

    id_to_record = {r.event_id: r for r in records}
    filtered: list[dict[str, Any]] = []
    for opp in opportunities:
        record = id_to_record.get(opp["id"])
        if record is None:
            continue
        event_date = _event_local_date(record, tz)
        if event_date == target:
            filtered.append(opp)
    return filtered


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
    all_opps: list[dict[str, Any]] = []
    for record in records:
        opp = _opportunity_from_record(record)
        if opp:
            all_opps.append(opp)

    today_opps = _filter_by_day(all_opps, records, day="today")
    tomorrow_opps = _filter_by_day(all_opps, records, day="tomorrow")
    active = today_opps if day == "today" else tomorrow_opps

    return {
        "day": day,
        "stats": _compute_stats(active),
        "counts": {
            "today": len(today_opps),
            "tomorrow": len(tomorrow_opps),
        },
        "opportunities": active,
        "last_run_at": _state.last_run_at.isoformat() if _state.last_run_at else None,
        "running": _state.running,
        "error": _state.last_error,
    }


def _persist_cache(records: list[UnifiedRecord]) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "last_run_at": _state.last_run_at.isoformat() if _state.last_run_at else None,
        "records": [r.to_export_dict() for r in records],
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
            records.append(UnifiedRecord.model_validate(item))
        if data.get("last_run_at"):
            _state.last_run_at = datetime.fromisoformat(str(data["last_run_at"]))
        return records
    except Exception as exc:
        logger.warning("Could not load cache: %s", exc)
        return []


async def execute_run(*, sport_key: str | None = None) -> None:
    if _state.running:
        return
    _state.running = True
    _state.last_error = None
    try:
        engine = HarvesterEngine()
        records = await engine.run(sport_key, arbs_only=False)
        _state.records = records
        _state.last_run_at = datetime.now(timezone.utc)
        _persist_cache(records)
    except Exception as exc:
        logger.exception("Dashboard run failed")
        _state.last_error = str(exc)
        raise
    finally:
        _state.running = False
