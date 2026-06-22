"""Sportsbook balance providers — mock JSON today, Pikkit adapter stub."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from harvester_paths import PACKAGE_DIR
from settings import get_settings
from target_sources import TARGET_SOURCE_KEYS

logger = logging.getLogger(__name__)

MOCK_BALANCES_PATH = PACKAGE_DIR / "data" / "mock_balances.json"
USER_BALANCES_PATH = PACKAGE_DIR / "data" / "user_balances.json"

DEFAULT_MOCK_BALANCES: dict[str, float] = {
    "draftkings": 850.0,
    "fanduel": 1200.0,
    "betmgm": 600.0,
    "caesars": 450.0,
    "fanatics": 300.0,
    "thescore": 250.0,
    "bet365": 0.0,
}


def _normalize_balances(raw: dict[str, Any]) -> dict[str, float]:
    out: dict[str, float] = {}
    for key, value in raw.items():
        try:
            amount = float(value)
        except (TypeError, ValueError):
            continue
        if amount < 0:
            continue
        out[str(key).strip().lower()] = round(amount, 2)
    return out


def load_mock_balances() -> dict[str, float]:
    if MOCK_BALANCES_PATH.is_file():
        try:
            data = json.loads(MOCK_BALANCES_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return _normalize_balances(data)
        except Exception as exc:
            logger.warning("Could not read mock balances: %s", exc)
    return dict(DEFAULT_MOCK_BALANCES)


def load_user_balances() -> dict[str, float] | None:
    if not USER_BALANCES_PATH.is_file():
        return None
    try:
        data = json.loads(USER_BALANCES_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return _normalize_balances(data)
    except Exception as exc:
        logger.warning("Could not read user balances: %s", exc)
    return None


def save_book_balances(balances: dict[str, float]) -> None:
    USER_BALANCES_PATH.parent.mkdir(parents=True, exist_ok=True)
    USER_BALANCES_PATH.write_text(
        json.dumps(_normalize_balances(balances), indent=2),
        encoding="utf-8",
    )


async def fetch_pikkit_balances() -> dict[str, float]:
    """
    Future: wire Pikkit API here.
    Returns empty dict until HARVESTER_PIKKIT_API_KEY is configured.
    """
    settings = get_settings()
    if not settings.pikkit_api_key:
        return {}
    logger.info("Pikkit balance adapter not implemented — using mock/user balances")
    return {}


def get_book_balances() -> dict[str, float]:
    """
    Resolve balances for the optimizer.

    Priority: user overrides → Pikkit (when implemented) → mock fixture.
    Always includes known target sources (missing books = $0).
    """
    settings = get_settings()
    balances: dict[str, float] = {}

    user = load_user_balances()
    if user:
        balances.update(user)

    provider = (settings.balance_provider or "mock").strip().lower()
    if provider == "pikkit" and settings.pikkit_api_key:
        # Sync stub — async fetch happens in API route when needed.
        pass

    if not balances:
        balances.update(load_mock_balances())

    resolved = {key: 0.0 for key in TARGET_SOURCE_KEYS}
    for key, amount in balances.items():
        if key in resolved:
            resolved[key] = amount
    return resolved


def balances_snapshot() -> dict[str, Any]:
    """API-friendly balance payload with display names."""
    from target_sources import TARGET_SOURCE_BY_KEY

    balances = get_book_balances()
    rows = []
    for key, amount in balances.items():
        src = TARGET_SOURCE_BY_KEY.get(key)
        rows.append(
            {
                "key": key,
                "name": src.name if src else key,
                "balance_usd": amount,
                "available": amount > 0,
            }
        )
    return {
        "provider": get_settings().balance_provider,
        "total_usd": round(sum(balances.values()), 2),
        "books": rows,
    }
