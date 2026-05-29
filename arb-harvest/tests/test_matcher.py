from arb_harvest.models import NormalizedEvent, SourceBook
from arb_harvest.normalize import EventMatcher, build_normalized_event_name


def test_team_alias_normalization():
    name = build_normalized_event_name("CHA Hornets", "Boston Celtics", "basketball_nba")
    assert "charlotte hornets" in name
    assert "boston celtics" in name


def test_fuzzy_match_across_sources():
    matcher = EventMatcher(min_score=80)
    base = NormalizedEvent(
        event_id="1",
        sport_key="basketball_nba",
        normalized_name="",
        home_team="Charlotte Hornets",
        away_team="Boston Celtics",
        commence_time="2026-06-01T00:00:00Z",
        books=[],
    )
    index = matcher.index([base])
    cand = NormalizedEvent(
        event_id="2",
        sport_key="basketball_nba",
        normalized_name="",
        home_team="Hornets",
        away_team="Celtics",
        commence_time="2026-06-01T00:00:00Z",
        books=[
            SourceBook(source_id="polymarket", title="Polymarket", markets=[]),
        ],
    )
    hit = matcher.find_match(cand, index)
    assert hit is not None
    merged = matcher.merge_books(hit, cand)
    assert any(b.source_id == "polymarket" for b in merged.books)
