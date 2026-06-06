"""Tests for Polymarket normalization helpers."""

from integrators.polymarket import (
    market_matches_sport,
    normalize_polymarket_market,
    probability_to_decimal_odds,
)


def test_probability_to_decimal_odds() -> None:
    assert probability_to_decimal_odds(0.5) == 2.0
    assert probability_to_decimal_odds(0.0) is None
    assert probability_to_decimal_odds(1.0) is None


def test_normalize_polymarket_market_gamma_shape() -> None:
    raw = {
        "conditionId": "0xabc",
        "question": "Will Team A beat Team B?",
        "outcomes": '["Yes", "No"]',
        "outcomePrices": '["0.55", "0.45"]',
        "clobTokenIds": '["111", "222"]',
        "active": True,
        "closed": False,
        "slug": "nba-team-a-b",
    }
    norm = normalize_polymarket_market(raw)
    assert norm["event_id"] == "0xabc"
    assert norm["platform"] == "polymarket"
    assert len(norm["outcomes"]) == 2
    assert norm["outcomes"][0]["probability"] == 0.55
    assert norm["outcomes"][0]["token_id"] == "111"


def test_market_matches_sport_nba() -> None:
    assert market_matches_sport({"question": "NBA Finals winner"}, "basketball_nba")
    assert not market_matches_sport({"question": "New Rihanna Album"}, "basketball_nba")
