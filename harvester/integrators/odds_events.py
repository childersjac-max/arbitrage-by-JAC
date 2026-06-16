"""Shared Odds-API-shaped event payload → UnifiedRecord conversion."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from models import SourceQuote, UnifiedRecord


def parse_commence(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        text = value.replace("Z", "+00:00")
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def normalize_decimal_price(price: float) -> float:
    """Convert American odds to decimal when needed; pass through decimal prices."""
    if price == 0:
        return price
    if price < 0:
        return round(1.0 + (100.0 / abs(price)), 4)
    if price >= 100:
        return round(1.0 + (price / 100.0), 4)
    if price > 1.0:
        return round(price, 4)
    return price


def event_display_name(home: str, away: str) -> str:
    return f"{away} @ {home}"


def event_dict_to_record(
    event: dict[str, Any],
    sport_key: str,
    *,
    market_type: str | None = None,
    metadata_extra: dict[str, Any] | None = None,
) -> UnifiedRecord:
    home = str(event.get("home_team") or "")
    away = str(event.get("away_team") or "")
    event_id = str(event.get("id") or f"{sport_key}:{home}:{away}")
    commence = parse_commence(event.get("commence_time"))
    display = event_display_name(home, away)

    by_book: dict[str, list[SourceQuote]] = {}
    for bookmaker in event.get("bookmakers") or []:
        if not isinstance(bookmaker, dict):
            continue
        book_key = str(bookmaker.get("key") or "unknown")
        book_quotes: list[SourceQuote] = []
        for market in bookmaker.get("markets") or []:
            if not isinstance(market, dict):
                continue
            market_key = str(market.get("key") or "h2h")
            for outcome in market.get("outcomes") or []:
                if not isinstance(outcome, dict):
                    continue
                name = str(outcome.get("name") or "")
                price = outcome.get("price")
                if price is None:
                    continue
                book_quotes.append(
                    SourceQuote(
                        source=book_key,
                        outcome=name,
                        price=normalize_decimal_price(float(price)),
                        line=outcome.get("point"),
                        raw_label=name,
                    )
                )
        if book_quotes:
            by_book[book_key] = book_quotes

    primary_market = market_type or "h2h"
    if not market_type and by_book:
        first_book = next(iter(event.get("bookmakers") or []), {})
        if isinstance(first_book, dict) and first_book.get("markets"):
            m0 = first_book["markets"][0]
            if isinstance(m0, dict) and m0.get("key"):
                primary_market = str(m0["key"])

    metadata: dict[str, Any] = {"home_team": home, "away_team": away}
    if metadata_extra:
        metadata.update(metadata_extra)

    return UnifiedRecord(
        timestamp=datetime.now(timezone.utc),
        event_id=event_id,
        sport_key=sport_key,
        normalized_event_name=display,
        market_type=primary_market,
        commence_time=commence,
        sources=by_book,
        metadata=metadata,
    )
