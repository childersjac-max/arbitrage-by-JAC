"""Timezone helpers that work on Windows without bundled tzdata."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any


def get_tz(name: str | None = None) -> Any:
    """
    Return a tzinfo for filtering. Falls back to UTC if zoneinfo/tzdata unavailable.
    """
    key = (name or "America/New_York").strip() or "America/New_York"
    try:
        from zoneinfo import ZoneInfo

        return ZoneInfo(key)
    except Exception:
        return timezone.utc


def today_and_tomorrow(tz: Any) -> tuple[date, date]:
    now = datetime.now(tz)
    today = now.date()
    return today, today + timedelta(days=1)


def to_local_date(dt: datetime, tz: Any) -> date | None:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(tz).date()
