from arb_harvest.engine.arbitrage import detect_arbitrage
from arb_harvest.models import MarketQuote, NormalizedEvent, OutcomeQuote, SourceBook


def test_detects_two_way_arb():
    ev = NormalizedEvent(
        event_id="x",
        sport_key="basketball_nba",
        normalized_name="a vs b",
        home_team="A",
        away_team="B",
        commence_time="2026-06-01T00:00:00Z",
        books=[
            SourceBook(
                source_id="draftkings",
                title="DK",
                markets=[
                    MarketQuote(
                        key="h2h",
                        outcomes=[OutcomeQuote(name="A", price_american=150)],
                    )
                ],
            ),
            SourceBook(
                source_id="fanduel",
                title="FD",
                markets=[
                    MarketQuote(
                        key="h2h",
                        outcomes=[OutcomeQuote(name="B", price_american=150)],
                    )
                ],
            ),
        ],
    )
    signals = detect_arbitrage([ev], min_yield_pct=0.0)
    assert len(signals) == 1
    assert signals[0].calculated_arbitrage_yield_percentage > 0
