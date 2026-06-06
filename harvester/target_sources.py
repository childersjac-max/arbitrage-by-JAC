"""Canonical arbitrage source registry (user-defined platform list)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Category = Literal["us_sportsbook", "us_prediction", "p2p_exchange"]


@dataclass(frozen=True)
class TargetSource:
    key: str
    name: str
    category: Category
    odds_api_keys: tuple[str, ...]
    direct_only: bool = False
    integration_note: str = ""


def _s(
    key: str,
    name: str,
    category: Category,
    *odds_keys: str,
    direct_only: bool = False,
    note: str = "",
) -> TargetSource:
    return TargetSource(
        key=key,
        name=name,
        category=category,
        odds_api_keys=odds_keys or (key,),
        direct_only=direct_only,
        integration_note=note,
    )


TARGET_SOURCES: tuple[TargetSource, ...] = (
    # 1. US regulated sportsbooks
    _s("draftkings", "DraftKings", "us_sportsbook", "draftkings"),
    _s("fanduel", "FanDuel", "us_sportsbook", "fanduel"),
    _s("betmgm", "BetMGM", "us_sportsbook", "betmgm"),
    _s("caesars", "Caesars", "us_sportsbook", "williamhill_us", "caesars"),
    _s("fanatics", "Fanatics", "us_sportsbook", "fanatics"),
    _s(
        "bet365",
        "bet365",
        "us_sportsbook",
        "bet365",
        direct_only=True,
        note="US feed often region-limited; use licensed commercial API where available.",
    ),
    _s("thescore", "The Score", "us_sportsbook", "thescore", "espnbet"),
    # 2. Regulated US prediction markets
    _s(
        "kalshi",
        "Kalshi",
        "us_prediction",
        "kalshi",
        direct_only=True,
        note="Wire Kalshi REST API (kalshi.com/docs) for event-contract prices.",
    ),
    _s(
        "polymarket",
        "Polymarket",
        "us_prediction",
        "polymarket",
        direct_only=True,
        note="Live integrator: harvester/integrators/polymarket.py (Gamma + optional CLOB).",
    ),
    _s(
        "draftkings_predictions",
        "DraftKings Predictions",
        "us_prediction",
        direct_only=True,
        note="Use DraftKings prediction-market product API when licensed.",
    ),
    _s(
        "fanduel_prediction",
        "FanDuel Prediction",
        "us_prediction",
        direct_only=True,
        note="Use FanDuel prediction-market product API when licensed.",
    ),
    # 3. Peer-to-peer global exchanges
    _s(
        "betfair_exchange",
        "Betfair Exchange",
        "p2p_exchange",
        "betfair_ex_uk",
        "betfair",
        direct_only=True,
        note="Betfair Exchange API (developer.betfair.com).",
    ),
    _s(
        "smarkets",
        "Smarkets",
        "p2p_exchange",
        "smarkets",
        direct_only=True,
        note="Smarkets Exchange API — commercial access required.",
    ),
    _s(
        "sportx",
        "SportX / SX Bet",
        "p2p_exchange",
        "sportx",
        direct_only=True,
        note="SportX / SX Bet API for peer-to-peer sports markets.",
    ),
)

TARGET_SOURCE_BY_KEY: dict[str, TargetSource] = {s.key: s for s in TARGET_SOURCES}

# Map Odds API bookmaker key -> canonical target key
ODDS_API_KEY_TO_TARGET: dict[str, str] = {}
for src in TARGET_SOURCES:
    for alias in src.odds_api_keys:
        ODDS_API_KEY_TO_TARGET[alias] = src.key

TARGET_SOURCE_KEYS: tuple[str, ...] = tuple(s.key for s in TARGET_SOURCES)

CATEGORY_LABELS: dict[str, str] = {
    "us_sportsbook": "US Regulated Sportsbooks",
    "us_prediction": "Regulated US Prediction Markets",
    "p2p_exchange": "Peer-to-Peer Global Exchanges",
}
