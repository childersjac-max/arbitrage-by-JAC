"""Entity resolution across books and prediction markets."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from rapidfuzz import fuzz

# Common abbreviations / nicknames → token for matching
ALIASES: dict[str, str] = {
    "cha": "hornets",
    "charlotte": "hornets",
    "hornets": "hornets",
    "la": "lakers",
    "lakers": "lakers",
    "los angeles lakers": "lakers",
    "gsw": "warriors",
    "golden state": "warriors",
}


@dataclass(frozen=True)
class EventIdentity:
    sport: str
    home_slug: str
    away_slug: str
    league: str | None = None

    @property
    def key(self) -> str:
        lg = self.league or ""
        return f"{self.sport}|{lg}|{self.away_slug}@{self.home_slug}"


def _strip_accents(text: str) -> str:
    nf = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nf if not unicodedata.combining(c))


def normalize_team_name(name: str) -> str:
    s = _strip_accents(name.lower().strip())
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    for token in s.split():
        if token in ALIASES:
            return ALIASES[token]
    # Drop city prefixes: keep last meaningful token(s)
    parts = s.split()
    if len(parts) >= 2:
        return " ".join(parts[-2:]) if len(parts[-1]) <= 4 else parts[-1]
    return s


def slug_team(name: str) -> str:
    base = normalize_team_name(name)
    return re.sub(r"[^a-z0-9]+", "_", base).strip("_")


def build_event_identity(
    sport: str,
    home: str,
    away: str,
    league: str | None = None,
) -> EventIdentity:
    h, a = slug_team(home), slug_team(away)
    # Canonical home@away ordering for stable keys
    if a > h:
        h, a = a, h
    return EventIdentity(sport=sport.lower(), home_slug=h, away_slug=a, league=league)


def event_display_name(home: str, away: str) -> str:
    return f"{away} @ {home}"


def match_event_titles(
    haystack: str,
    home: str,
    away: str,
    *,
    threshold: int = 82,
) -> bool:
    """True if haystack refers to the same fixture (fuzzy)."""
    hay = haystack.lower()
    h = normalize_team_name(home)
    a = normalize_team_name(away)
    if h in hay and a in hay:
        return True
    target = f"{away} vs {home}".lower()
    return fuzz.partial_ratio(hay, target) >= threshold
