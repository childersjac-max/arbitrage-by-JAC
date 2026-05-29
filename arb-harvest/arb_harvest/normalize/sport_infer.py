"""Infer Odds API sport_key from free-text titles."""

from __future__ import annotations

import re

NBA_TEAMS = (
    "hawks", "celtics", "nets", "hornets", "bulls", "cavaliers", "cavs",
    "mavericks", "mavs", "nuggets", "pistons", "warriors", "rockets", "pacers",
    "clippers", "lakers", "grizzlies", "heat", "bucks", "timberwolves", "wolves",
    "pelicans", "knicks", "thunder", "magic", "76ers", "sixers", "suns", "blazers",
    "kings", "spurs", "raptors", "jazz", "wizards",
)

NFL_TEAMS = (
    "chiefs", "49ers", "cowboys", "eagles", "ravens", "bills", "dolphins",
    "packers", "lions", "vikings", "bears", "rams", "chargers", "raiders",
    "broncos", "patriots", "jets", "giants", "commanders", "bengals", "browns",
    "steelers", "texans", "colts", "jaguars", "titans", "saints", "falcons",
    "panthers", "buccaneers", "cardinals", "seahawks",
)


def infer_sport_key(text: str, league_hint: str | None = None) -> str:
    blob = f"{text} {league_hint or ''}".lower()
    if re.search(r"\bnba\b", blob):
        return "basketball_nba"
    if re.search(r"\bnfl\b", blob):
        return "americanfootball_nfl"
    if re.search(r"\bnhl\b", blob):
        return "icehockey_nhl"
    if re.search(r"\bmlb\b", blob):
        return "baseball_mlb"
    if "basketball" in blob:
        return "basketball_nba"
    if "football" in blob and "soccer" not in blob:
        return "americanfootball_nfl"
    nba_hits = sum(1 for t in NBA_TEAMS if t in blob)
    nfl_hits = sum(1 for t in NFL_TEAMS if t in blob)
    if nba_hits >= 2 or (nba_hits >= 1 and nfl_hits == 0):
        return "basketball_nba"
    if nfl_hits >= 2:
        return "americanfootball_nfl"
    return "unknown"
