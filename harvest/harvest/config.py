"""Environment-driven configuration for harvest extractors."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


NC_SPORTSBOOKS = (
    "draftkings",
    "fanduel",
    "betmgm",
    "caesars",
    "bet365",
    "fanatics",
    "thescore",
)

SCAN_TARGETS: list[tuple[str, list[str]]] = [
    ("baseball", ["mlb"]),
    ("basketball", ["nba", "wnba"]),
    ("football", ["nfl"]),
    ("hockey", ["nhl"]),
    ("golf", ["pga"]),
    ("soccer", ["mls", "epl", "uefa_champs_league"]),
]


@dataclass
class HarvestConfig:
    optic_odds_api_key: str | None = field(
        default_factory=lambda: os.getenv("ODDSJAM_API_KEY") or os.getenv("OPTIC_ODDS_API_KEY")
    )
    betfair_app_key: str | None = field(default_factory=lambda: os.getenv("BETFAIR_APP_KEY"))
    betfair_session_token: str | None = field(
        default_factory=lambda: os.getenv("BETFAIR_SESSION_TOKEN")
    )
    smarkets_api_key: str | None = field(default_factory=lambda: os.getenv("SMARKETS_API_KEY"))
    sportx_api_key: str | None = field(default_factory=lambda: os.getenv("SPORTX_API_KEY"))
    request_timeout_s: float = 30.0
    max_workers: int = 8
    fuzzy_match_threshold: int = 82
    enable_optic: bool = True
    enable_kalshi: bool = True
    enable_polymarket: bool = True
    enable_betfair: bool = True
    enable_smarkets: bool = False
    enable_sportx: bool = False

    @classmethod
    def from_env(cls) -> HarvestConfig:
        return cls()


def configured_sources(cfg: HarvestConfig) -> list[str]:
    sources: list[str] = []
    if cfg.enable_optic and cfg.optic_odds_api_key:
        sources.extend(NC_SPORTSBOOKS)
    if cfg.enable_kalshi:
        sources.append("kalshi")
    if cfg.enable_polymarket:
        sources.append("polymarket")
    if cfg.enable_betfair and cfg.betfair_app_key and cfg.betfair_session_token:
        sources.append("betfair_exchange")
    if cfg.enable_smarkets and cfg.smarkets_api_key:
        sources.append("smarkets")
    if cfg.enable_sportx and cfg.sportx_api_key:
        sources.append("sportx")
    return sources
