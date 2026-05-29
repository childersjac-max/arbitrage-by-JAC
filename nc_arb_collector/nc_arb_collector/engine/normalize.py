"""
Cross-platform entity normalization — maps variant team/market names
to canonical keys for splice matching.
"""

from __future__ import annotations

import re
import unicodedata

from rapidfuzz import fuzz

# NCAA / pro aliases common across books and prediction markets
TEAM_ALIASES: dict[str, str] = {
    "nc state": "north carolina state",
    "n.c. state": "north carolina state",
    "unc": "north carolina",
    "unc chapel hill": "north carolina",
    "uconn": "connecticut",
    "usc": "southern california",
    "lsu": "louisiana state",
    "ole miss": "mississippi",
    "pitt": "pittsburgh",
    "va tech": "virginia tech",
    "vt": "virginia tech",
    "oklahoma city thunder": "oklahoma city thunder",
    "la clippers": "los angeles clippers",
    "la lakers": "los angeles lakers",
    "la chargers": "los angeles chargers",
    "la rams": "los angeles rams",
}

MARKET_ALIASES: dict[str, str] = {
    "moneyline": "h2h",
    "ml": "h2h",
    "head to head": "h2h",
    "spread": "spreads",
    "point spread": "spreads",
    "total": "totals",
    "over/under": "totals",
    "game total": "totals",
}


def _strip_accents(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def normalize_token(text: str) -> str:
    t = _strip_accents(text.lower().strip())
    t = re.sub(r"[^\w\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return TEAM_ALIASES.get(t, t)


def normalize_team(name: str) -> str:
    return normalize_token(name)


def normalize_market_type(market: str) -> str:
    key = normalize_token(market)
    return MARKET_ALIASES.get(key, key)


def event_match_key(home: str, away: str, market_type: str) -> str:
    teams = sorted([normalize_team(home), normalize_team(away)])
    m = normalize_market_type(market_type)
    return f"{teams[0]}|{teams[1]}|{m}"


def normalized_event_display(home: str, away: str) -> str:
    return f"{home.strip()} vs {away.strip()}"


def teams_match(a_home: str, a_away: str, b_home: str, b_away: str, threshold: int = 82) -> bool:
    """Fuzzy match when metadata uses different naming (e.g. Kalshi titles)."""
    key_a = event_match_key(a_home, a_away, "h2h")
    key_b = event_match_key(b_home, b_away, "h2h")
    if key_a == key_b:
        return True
    disp_a = normalized_event_display(a_home, a_away).lower()
    disp_b = normalized_event_display(b_home, b_away).lower()
    return fuzz.token_set_ratio(disp_a, disp_b) >= threshold


def match_outcome_names(a: str, b: str) -> bool:
    na, nb = normalize_token(a), normalize_token(b)
    if na == nb:
        return True
    if na in nb or nb in na:
        return True
    return fuzz.ratio(na, nb) >= 85
