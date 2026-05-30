"""Tests for quote merge behavior."""

from datetime import datetime, timezone

import pytest

from harvester.models import MarketType, SourceQuote
from harvester.orchestrator import merge_quotes


class StaticNormalizer:
    """Test normalizer with deterministic alias outputs."""

    async def normalize_batch(self, fragments):
        """Return canonical forms for known fragments."""

        mapping = {
            "LA Lakers @ BOS Celtics": "Los Angeles Lakers @ Boston Celtics",
            "Los Angeles Lakers at Boston Celtics": "Los Angeles Lakers @ Boston Celtics",
            "BOS Celtics": "Boston Celtics",
        }
        return {fragment: mapping.get(fragment, fragment) for fragment in fragments}


@pytest.mark.asyncio
async def test_merge_groups_by_normalized_event_and_time_window() -> None:
    """Different raw names for the same event merge into one unified output."""

    start = datetime(2026, 6, 1, 0, 7, tzinfo=timezone.utc)
    quotes = [
        SourceQuote(
            source_id="the_odds_api:draftkings",
            sport="basketball_nba",
            raw_event_id="a",
            raw_event_name="LA Lakers @ BOS Celtics",
            start_time=start,
            market_type=MarketType.MONEYLINE,
            selection_name="BOS Celtics",
            odds=120,
            fetched_at=start,
        ),
        SourceQuote(
            source_id="the_odds_api:fanduel",
            sport="basketball_nba",
            raw_event_id="b",
            raw_event_name="Los Angeles Lakers at Boston Celtics",
            start_time=start.replace(minute=22),
            market_type=MarketType.MONEYLINE,
            selection_name="BOS Celtics",
            odds=118,
            fetched_at=start,
        ),
    ]

    merged = await merge_quotes(quotes, normalizer=StaticNormalizer(), window_minutes=30)

    assert len(merged) == 1
    event = merged[0]
    assert event.normalized_event_name == "Los Angeles Lakers @ Boston Celtics"
    assert event.selection_name == "Boston Celtics"
    assert set(event.sources) == {"the_odds_api:draftkings", "the_odds_api:fanduel"}
    assert event.start_time.minute == 0
