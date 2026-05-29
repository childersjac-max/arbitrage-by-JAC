"""Puzzle-piece assembly: merge metadata-rich and price-fast fragments."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, replace

from harvest.fuzzy import build_event_identity, event_display_name
from harvest.models import MarketFragment


@dataclass
class SplicedBoard:
    by_event: dict[str, list[MarketFragment]]


def splice_fragments(
    fragments: list[MarketFragment],
    *,
    prefer_metadata_source: str | None = None,
) -> SplicedBoard:
    """
    Merge uneven streams:
    - Sportsbook fragments supply team names, league, commence_time
    - Prediction markets supply yes/no prices matched by fuzzy title
    - Exchanges supply back/lay depth when present
    """
    by_key: dict[str, list[MarketFragment]] = defaultdict(list)
    canonical_meta: dict[str, MarketFragment] = {}

    for frag in fragments:
        ident = build_event_identity(
            frag.sport if frag.sport != "unknown" else "multi",
            frag.home_team,
            frag.away_team,
            frag.league,
        )
        by_key[ident.key].append(frag)

    for key, group in by_key.items():
        meta = _pick_canonical_meta(group, prefer_metadata_source)
        if meta:
            canonical_meta[key] = meta

    merged: dict[str, list[MarketFragment]] = {}
    for key, group in by_key.items():
        meta = canonical_meta.get(key)
        out: list[MarketFragment] = []
        for frag in group:
            if meta and frag is not meta and frag.sport == "unknown":
                out.append(
                    replace(
                        frag,
                        sport=meta.sport,
                        league=meta.league,
                        home_team=meta.home_team,
                        away_team=meta.away_team,
                        commence_time=frag.commence_time or meta.commence_time,
                        metadata={**frag.metadata, "spliced_meta_from": meta.source},
                    )
                )
            else:
                out.append(frag)
        merged[key] = out

    return SplicedBoard(by_event=merged)


def _pick_canonical_meta(
    group: list[MarketFragment],
    prefer: str | None,
) -> MarketFragment | None:
    sportsbooks = [g for g in group if g.sport != "unknown"]
    if prefer:
        for g in sportsbooks:
            if g.source == prefer:
                return g
    with_league = [g for g in sportsbooks if g.league]
    return with_league[0] if with_league else (sportsbooks[0] if sportsbooks else None)


def board_display_names(board: SplicedBoard) -> dict[str, str]:
    names: dict[str, str] = {}
    for key, frags in board.by_event.items():
        if not frags:
            continue
        f = frags[0]
        names[key] = event_display_name(f.home_team, f.away_team)
    return names
