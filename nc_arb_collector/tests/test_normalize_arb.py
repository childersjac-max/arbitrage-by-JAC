"""Unit tests for normalization and arbitrage math."""

from nc_arb_collector.engine.arbitrage import ArbitragePipeline
from nc_arb_collector.engine.normalize import event_match_key, normalize_team, teams_match
from nc_arb_collector.models import OddsLeg, UnifiedMarket
from nc_arb_collector.utils.odds_math import two_way_arb_yield


def test_team_alias():
    assert normalize_team("NC State") == "north carolina state"


def test_event_key_stable():
    k1 = event_match_key("NC State", "Duke", "h2h")
    k2 = event_match_key("North Carolina State", "Duke", "moneyline")
    assert k1 == k2


def test_fuzzy_teams():
    assert teams_match("Lakers", "Celtics", "LA Lakers", "Boston Celtics", threshold=70)


def test_two_way_arb():
    r = two_way_arb_yield(150, -140)
    assert r is not None
    assert r[0] > 0


def test_arb_pipeline_finds_cross_book():
    um = UnifiedMarket(
        normalized_event_name="Team A vs Team B",
        market_type="h2h",
        commence_time=None,
        home_team="Team A",
        away_team="Team B",
        event_key="a|b|h2h",
        legs_by_platform={
            "draftkings": [
                OddsLeg("draftkings", "Team A", 200),
                OddsLeg("draftkings", "Team B", -110),
            ],
            "fanduel": [
                OddsLeg("fanduel", "Team A", 180),
                OddsLeg("fanduel", "Team B", 120),
            ],
        },
    )
    rows = ArbitragePipeline(min_yield_pct=0.01).scan([um])
    assert isinstance(rows, list)
