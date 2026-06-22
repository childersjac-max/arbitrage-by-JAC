"""Build per-source status for the dashboard Sources tab."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from models import UnifiedRecord
from settings import get_settings
from target_sources import CATEGORY_LABELS, ODDS_API_KEY_TO_TARGET, TARGET_SOURCES, TargetSource


def _books_used_in_arbitrage(records: list[UnifiedRecord]) -> set[str]:
    used: set[str] = set()
    for record in records:
        if not record.arbitrage:
            continue
        for leg in record.arbitrage.legs:
            used.add(leg.source)
        for key in record.metadata.get("sources_used") or []:
            used.add(str(key))
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


def _row_for_target(
    src: TargetSource,
    stats: dict[str, dict[str, int]],
    arb_books: set[str],
    *,
    api_error: str | None,
) -> dict[str, Any]:
    settings = get_settings()
    channel = "direct" if src.direct_only else (
        "perplexity" if settings.effective_odds_provider() == "perplexity" else "odds_api"
    )
    display = src.name

    if api_error:
        return {
            "key": src.key,
            "name": display,
            "category": src.category,
            "category_label": CATEGORY_LABELS.get(src.category, src.category),
            "channel": channel,
            "status": "error",
            "status_label": "Error",
            "message": f"Unavailable — {api_error}",
            "events_with_odds": 0,
            "used_in_arbitrage": False,
        }

    if src.direct_only:
        book = stats.get(src.key)
        if book and book["events"] > 0:
            msg = f"Odds present for {book['events']} event(s) — {book['quotes']} line(s)"
            if src.key in arb_books:
                msg += " · used in LLM/math arbitrage scan"
            return {
                "key": src.key,
                "name": display,
                "category": src.category,
                "category_label": CATEGORY_LABELS.get(src.category, src.category),
                "channel": channel,
                "status": "loaded",
                "status_label": "Successfully loaded",
                "message": msg,
                "events_with_odds": book["events"],
                "used_in_arbitrage": src.key in arb_books,
            }
        return {
            "key": src.key,
            "name": display,
            "category": src.category,
            "category_label": CATEGORY_LABELS.get(src.category, src.category),
            "channel": channel,
            "status": "stub",
            "status_label": "Not connected",
            "message": src.integration_note or "Direct adapter not wired yet.",
            "events_with_odds": 0,
            "used_in_arbitrage": False,
        }

    book = stats.get(src.key)
    if book and book["events"] > 0:
        msg = f"Odds loaded for {book['events']} event(s), {book['quotes']} line(s)"
        if src.key in arb_books:
            msg += " · considered by local LLM arbitrage"
        return {
            "key": src.key,
            "name": display,
            "category": src.category,
            "category_label": CATEGORY_LABELS.get(src.category, src.category),
            "channel": channel,
            "status": "loaded",
            "status_label": "Successfully loaded",
            "message": msg,
            "events_with_odds": book["events"],
            "used_in_arbitrage": src.key in arb_books,
        }

    aliases = ", ".join(src.odds_api_keys)
    gateway = get_settings().odds_gateway_label()
    return {
        "key": src.key,
        "name": display,
        "category": src.category,
        "category_label": CATEGORY_LABELS.get(src.category, src.category),
        "channel": channel,
        "status": "empty",
        "status_label": "No odds returned",
        "message": f"Not in this run ({gateway} keys: {aliases})",
        "events_with_odds": 0,
        "used_in_arbitrage": False,
    }


def build_source_report(
    records: list[UnifiedRecord],
    *,
    api_error: str | None = None,
) -> list[dict[str, Any]]:
    """Status rows grouped by user target platform list."""
    report: list[dict[str, Any]] = []
    stats = _aggregate_book_stats(records)
    arb_books = _books_used_in_arbitrage(records)

    if api_error:
        gateway_status, gateway_label, gateway_msg = "error", "Error", api_error
    elif records:
        gateway_status, gateway_label, gateway_msg = (
            "loaded",
            "Successfully loaded",
            f"{len(records)} events · local LLM arbitrage enabled",
        )
    else:
        gateway_status, gateway_label, gateway_msg = (
            "empty",
            "No data",
            "API responded but returned no events for this sport",
        )

    report.append(
        {
            "key": get_settings().odds_gateway_key(),
            "name": get_settings().odds_gateway_label(),
            "category": "gateway",
            "category_label": "Data gateway",
            "channel": "gateway",
            "status": gateway_status,
            "status_label": gateway_label,
            "message": gateway_msg,
            "events_with_odds": len(records),
            "used_in_arbitrage": False,
        }
    )

    report.append(
        {
            "key": "local_llm",
            "name": "Local LLM (Ollama)",
            "category": "gateway",
            "category_label": "Analysis",
            "channel": "gateway",
            "status": "loaded" if records and not api_error else "empty",
            "status_label": "Considers arbs" if records else "Waiting for data",
            "message": "Scores cross-source opportunities among target platforms",
            "events_with_odds": len(records),
            "used_in_arbitrage": bool(arb_books),
        }
    )

    for src in TARGET_SOURCES:
        report.append(_row_for_target(src, stats, arb_books, api_error=api_error))

    # Extra Odds API books not in target list
    seen = {s.key for s in TARGET_SOURCES}
    for raw_key, book in sorted(stats.items()):
        if raw_key in seen:
            continue
        canonical = ODDS_API_KEY_TO_TARGET.get(raw_key, raw_key)
        if canonical in seen:
            continue
        report.append(
            {
                "key": raw_key,
                "name": raw_key.replace("_", " ").title(),
                "category": "other",
                "category_label": "Other (not in target list)",
                "channel": "odds_api",
                "status": "loaded",
                "status_label": "Successfully loaded",
                "message": f"{book['events']} event(s) — excluded from target-source LLM scan",
                "events_with_odds": book["events"],
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
