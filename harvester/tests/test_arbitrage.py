"""Tests for arbitrage yield calculations."""

from datetime import datetime, timezone

from harvester.models import MarketType, SourceSnapshot
from harvester.orchestrator import compute_arbitrage


def snapshot(price: float) -> SourceSnapshot:
    """Build a minimal source snapshot for tests."""

    return SourceSnapshot(
        raw_event_name="Team A @ Team B",
        odds=price,
        fetched_at=datetime(2026, 5, 30, tzinfo=timezone.utc),
    )


def test_binary_back_lay_yield_math() -> None:
    """Binary prices produce spread-based yield when two sources disagree."""

    block = compute_arbitrage(
        {
            "polymarket_public": snapshot(0.62),
            "kalshi_public": snapshot(0.55),
        },
        MarketType.BINARY_YES_NO,
    )

    assert block is not None
    assert block.best_back.source == "polymarket_public"
    assert block.best_lay.source == "kalshi_public"
    assert block.yield_pct == 7.0


def test_non_binary_markets_omit_arbitrage_block() -> None:
    """American bookmaker odds are not treated as lay-side exchange prices."""

    block = compute_arbitrage(
        {
            "the_odds_api:draftkings": snapshot(110),
            "the_odds_api:fanduel": snapshot(115),
        },
        MarketType.MONEYLINE,
    )

    assert block is None
