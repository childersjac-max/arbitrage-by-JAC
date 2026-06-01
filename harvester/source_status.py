"""Build per-source status for the dashboard Sources tab."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from integrators.stubs import STUB_SPECS
from models import UnifiedRecord

# Display names for Odds API bookmaker keys (US region common keys).
BOOKMAKER_DISPLAY: dict[str, str] = {
    "draftkings": "DraftKings",
    "fanduel": "FanDuel",
    "betmgm": "BetMGM",
    "fanatics": "Fanatics",
    "williamhill_us": "Caesars (William Hill US)",
    "caesars": "Caesars",
    "betrivers": "BetRivers",
    "bovada": "Bovada",
    "betonlineag": "BetOnline.ag",
    "mybookieag": "MyBookie.ag",
    "lowvig": "LowVig.ag",
    "pointsbetus": "PointsBet",
    "pointsbet": "PointsBet",
    "espnbet": "ESPN BET",
    "wynnbet": "WynnBET",
    "superbook": "SuperBook",
    "twinspires": "TwinSpires",
    "barstool": "Barstool",
    "unibet_us": "Unibet US",
    "foxbet": "FOX Bet",
    "fliff": "Fliff",
    "betus": "BetUS",
    "hardrockbet": "Hard Rock Bet",
}

# Bookmakers we expect to evaluate when using The Odds API (US).
WATCHED_BOOKMAKER_KEYS: list[str] = [
    "draftkings",
    "fanduel",
    "betmgm",
    "fanatics",
    "williamhill_us",
    "betrivers",
    "bovada",
    "espnbet",
    "pointsbetus",
    "betonlineag",
    "mybookieag",
    "lowvig",
    "hardrockbet",
    "fliff",
]

# Stubs that are direct adapters only (not expected as Odds API book keys).
DIRECT_STUB_KEYS: set[str] = {
    "kalshi",
    "polymarket",
    "betfair",
    "bet365",
    "unibet",
    "pinnacle",
}


def _display_name(key: str) -> str:
    if key in BOOKMAKER_DISPLAY:
        return BOOKMAKER_DISPLAY[key]
    return key.replace("_", " ").title()


def _books_used_in_arbitrage(records: list[UnifiedRecord]) -> set[str]:
    used: set[str] = set()
    for record in records:
        arb = record.arbitrage
        if not arb:
            continue
        for leg in arb.legs:
            used.add(leg.source)
    return used


def _aggregate_book_stats(records: list[UnifiedRecord]) -> dict[str, dict[str, int]]:
    stats: dict[str, dict[str, int]] = defaultdict(lambda: {"events": 0, "quotes": 0})
    for record in records:
        for book_key, quotes in record.sources.items():
            if not quotes:
                continue
            stats[book_key]["events"] += 1
            stats[book_key]["quotes"] += len(quotes)
    return stats


def build_source_report(
    records: list[UnifiedRecord],
    *,
    api_error: str | None = None,
) -> list[dict[str, Any]]:
    """
    Status rows for UI: gateway, Odds API bookmakers, and direct stub adapters.
    """
    report: list[dict[str, Any]] = []
    stats = _aggregate_book_stats(records)
    arb_books = _books_used_in_arbitrage(records)
    seen_keys: set[str] = set()

    # Gateway row
    if api_error:
        gateway_status = "error"
        gateway_label = "Error"
        gateway_msg = api_error
    elif records:
        gateway_status = "loaded"
        gateway_label = "Successfully loaded"
        gateway_msg = f"{len(records)} events fetched"
    else:
        gateway_status = "empty"
        gateway_label = "No data"
        gateway_msg = "API responded but returned no events for this sport"

    report.append(
        {
            "key": "the_odds_api",
            "name": "The Odds API",
            "channel": "gateway",
            "status": gateway_status,
            "status_label": gateway_label,
            "message": gateway_msg,
            "events_with_odds": len(records),
            "used_in_arbitrage": False,
        }
    )

    def _book_row(key: str, *, force_stub: bool = False) -> dict[str, Any]:
        seen_keys.add(key)
        display = _display_name(key)
        if api_error:
            return {
                "key": key,
                "name": display,
                "channel": "odds_api",
                "status": "error",
                "status_label": "Error",
                "message": f"Unavailable — {api_error}",
                "events_with_odds": 0,
                "used_in_arbitrage": False,
            }
        if force_stub:
            todo = next((t for k, t in STUB_SPECS if k == key), "Direct adapter not implemented.")
            return {
                "key": key,
                "name": display,
                "channel": "direct",
                "status": "stub",
                "status_label": "Not connected",
                "message": todo,
                "events_with_odds": 0,
                "used_in_arbitrage": False,
            }
        book = stats.get(key)
        if book and book["events"] > 0:
            msg = f"Odds loaded for {book['events']} event(s), {book['quotes']} line(s)"
            if key in arb_books:
                msg += " · used in arbitrage scan"
            return {
                "key": key,
                "name": display,
                "channel": "odds_api",
                "status": "loaded",
                "status_label": "Successfully loaded",
                "message": msg,
                "events_with_odds": book["events"],
                "used_in_arbitrage": key in arb_books,
            }
        return {
            "key": key,
            "name": display,
            "channel": "odds_api",
            "status": "empty",
            "status_label": "No odds returned",
            "message": "Not present in this run (region/market/sport may exclude this book)",
            "events_with_odds": 0,
            "used_in_arbitrage": False,
        }

    for key in WATCHED_BOOKMAKER_KEYS:
        if key in DIRECT_STUB_KEYS:
            continue
        report.append(_book_row(key))

    # Books that appeared in data but were not on the watchlist
    for key in sorted(stats.keys()):
        if key in seen_keys:
            continue
        report.append(_book_row(key))

    # Direct stub adapters (Kalshi, Polymarket, …)
    stub_todos = {k: t for k, t in STUB_SPECS}
    for key, todo in sorted(stub_todos.items()):
        if key in seen_keys:
            continue
        if key in stats and stats[key]["events"] > 0:
            report.append(_book_row(key))
            continue
        if key in WATCHED_BOOKMAKER_KEYS:
            continue
        report.append(
            {
                "key": key,
                "name": _display_name(key),
                "channel": "direct",
                "status": "stub",
                "status_label": "Not connected",
                "message": todo,
                "events_with_odds": 0,
                "used_in_arbitrage": False,
            }
        )

    return report


def source_summary(sources: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"loaded": 0, "empty": 0, "error": 0, "stub": 0}
    for row in sources:
        status = row.get("status") or ""
        if status in counts:
            counts[status] += 1
    return counts
