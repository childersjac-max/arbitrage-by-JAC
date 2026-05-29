"""Fuzzy event matching across books and prediction markets."""

from __future__ import annotations

import re
from dataclasses import dataclass

from rapidfuzz import fuzz

from arb_harvest.models import NormalizedEvent
from arb_harvest.normalize.team_aliases import LEAGUE_ALIASES


def _clean(text: str) -> str:
    t = text.lower().strip()
    t = re.sub(r"[^\w\s]", " ", t)
    t = re.sub(r"\s+", " ", t)
    return t


def normalize_team_token(name: str, sport_key: str | None = None) -> str:
    token = _clean(name)
    if sport_key:
        aliases = LEAGUE_ALIASES.get(sport_key, {})
        if token in aliases:
            return aliases[token]
        for part in token.split():
            if part in aliases:
                return aliases[part]
    return token


def build_normalized_event_name(home: str, away: str, sport_key: str | None = None) -> str:
    h = normalize_team_token(home, sport_key)
    a = normalize_team_token(away, sport_key)
    teams = sorted([h, a])
    return f"{teams[0]} vs {teams[1]}"


@dataclass
class EventMatcher:
    """Index events by normalized name + fuzzy fallback."""

    min_score: int = 86

    def _signature(self, ev: NormalizedEvent) -> str:
        return build_normalized_event_name(ev.home_team, ev.away_team, ev.sport_key)

    def index(self, events: list[NormalizedEvent]) -> dict[str, NormalizedEvent]:
        idx: dict[str, NormalizedEvent] = {}
        for ev in events:
            sig = self._signature(ev)
            ev.normalized_name = sig
            idx[sig] = ev
        return idx

    def find_match(
        self,
        candidate: NormalizedEvent,
        index: dict[str, NormalizedEvent],
    ) -> NormalizedEvent | None:
        sig = self._signature(candidate)
        if sig in index:
            return index[sig]
        best: NormalizedEvent | None = None
        best_score = 0
        for key, ev in index.items():
            if ev.sport_key != candidate.sport_key:
                continue
            score = fuzz.token_set_ratio(sig, key)
            if score > best_score:
                best_score = score
                best = ev
        if best_score >= self.min_score:
            return best
        # Title-only fallback (prediction market phrasing)
        hay = _clean(f"{candidate.home_team} {candidate.away_team}")
        for ev in index.values():
            if ev.sport_key != candidate.sport_key:
                continue
            blob = _clean(f"{ev.home_team} {ev.away_team} {ev.normalized_name}")
            if normalize_team_token(candidate.home_team, candidate.sport_key) in blob and (
                normalize_team_token(candidate.away_team, candidate.sport_key) in blob
            ):
                return ev
        return None

    def merge_books(self, base: NormalizedEvent, incoming: NormalizedEvent) -> NormalizedEvent:
        by_source = {b.source_id: b for b in base.books}
        for book in incoming.books:
            ex = by_source.get(book.source_id)
            if ex:
                ex.markets.extend(book.markets)
            else:
                by_source[book.source_id] = book
        base.books = list(by_source.values())
        return base
