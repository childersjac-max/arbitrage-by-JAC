"""Runtime configuration from environment."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return float(raw)


def _int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


# The Odds API bookmaker keys for US retail books in scope
US_SPORTSBOOK_KEYS = frozenset(
    {
        "draftkings",
        "fanduel",
        "betmgm",
        "williamhill_us",  # Caesars
        "fanatics",
        "bet365",
        "espnbet",  # ESPN Bet / The Score alignment varies by region
    }
)

DEFAULT_SPORT_KEYS = (
    "basketball_nba",
    "americanfootball_nfl",
    "icehockey_nhl",
    "baseball_mlb",
)


@dataclass(frozen=True)
class HarvestConfig:
    odds_api_key: str
    sport_keys: tuple[str, ...] = DEFAULT_SPORT_KEYS
    regions: str = "us"
    baseline_markets: tuple[str, ...] = ("h2h", "spreads", "totals")
    poll_interval_sec: float = 45.0
    min_arb_yield_pct: float = 0.25
    http_rps: float = 2.0
    max_workers: int = 8
    enable_kalshi: bool = True
    enable_polymarket: bool = True
    enable_event_props: bool = True
    prop_markets_by_sport: dict[str, tuple[str, ...]] = field(
        default_factory=lambda: {
            "basketball_nba": (
                "player_points",
                "player_rebounds",
                "player_assists",
                "player_threes",
            ),
            "americanfootball_nfl": (
                "player_pass_yds",
                "player_rush_yds",
                "player_reception_yds",
            ),
            "baseball_mlb": (
                "batter_hits",
                "pitcher_strikeouts",
            ),
        }
    )

    @classmethod
    def from_env(cls) -> HarvestConfig:
        key = os.environ.get("ODDS_API_KEY", "").strip()
        sports_raw = os.environ.get("ARB_SPORT_KEYS", "").strip()
        sport_keys = (
            tuple(s.strip() for s in sports_raw.split(",") if s.strip())
            if sports_raw
            else DEFAULT_SPORT_KEYS
        )
        return cls(
            odds_api_key=key,
            sport_keys=sport_keys,
            poll_interval_sec=_float("ARB_POLL_INTERVAL_SEC", 45.0),
            min_arb_yield_pct=_float("ARB_MIN_YIELD_PCT", 0.25),
            http_rps=_float("ARB_HTTP_RPS", 2.0),
            max_workers=_int("ARB_MAX_WORKERS", 8),
            enable_kalshi=os.environ.get("ARB_ENABLE_KALSHI", "1").strip()
            not in ("0", "false", "False"),
            enable_polymarket=os.environ.get("ARB_ENABLE_POLYMARKET", "1").strip()
            not in ("0", "false", "False"),
            enable_event_props=os.environ.get("ARB_ENABLE_EVENT_PROPS", "1").strip()
            not in ("0", "false", "False"),
        )
