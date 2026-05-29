"""Runtime configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


NC_SPORTSBOOK_REGION = "us"
NC_BOOK_KEYS = ("draftkings", "fanduel", "betmgm")

# Default sports for NC-relevant scan (override via NC_ARB_SPORT_KEYS comma list)
DEFAULT_SPORT_KEYS = (
    "americanfootball_nfl",
    "basketball_nba",
    "basketball_ncaab",
    "baseball_mlb",
    "icehockey_nhl",
    "mma_mixed_martial_arts",
    "soccer_usa_mls",
)


@dataclass
class CollectorConfig:
    """Central configuration for the orchestration loop."""

    odds_api_key: str = ""
    kalshi_base_url: str = "https://api.elections.kalshi.com/trade-api/v2"
    predictit_base_url: str = "https://www.predictit.org/api/marketdata"
    forecastex_data_base: str = "https://www.forecastex.com/data"
    sport_keys: tuple[str, ...] = DEFAULT_SPORT_KEYS
    markets: tuple[str, ...] = ("h2h", "spreads", "totals")
    poll_interval_sec: float = 45.0
    min_arb_yield_pct: float = 0.5
    request_timeout_sec: float = 20.0
    max_retries: int = 4
    use_curl_cffi: bool = True
    proxy_url: str | None = None
    ibkr_enabled: bool = False

    @classmethod
    def from_env(cls) -> CollectorConfig:
        sports = os.environ.get("NC_ARB_SPORT_KEYS", "")
        sport_keys = tuple(s.strip() for s in sports.split(",") if s.strip()) or DEFAULT_SPORT_KEYS
        markets = os.environ.get("NC_ARB_MARKETS", "h2h,spreads,totals")
        return cls(
            odds_api_key=os.environ.get("ODDS_API_KEY", os.environ.get("THE_ODDS_API_KEY", "")),
            kalshi_base_url=os.environ.get(
                "KALSHI_API_BASE",
                "https://api.elections.kalshi.com/trade-api/v2",
            ),
            sport_keys=sport_keys,
            markets=tuple(m.strip() for m in markets.split(",") if m.strip()),
            poll_interval_sec=float(os.environ.get("NC_ARB_POLL_SEC", "45")),
            min_arb_yield_pct=float(os.environ.get("NC_ARB_MIN_YIELD_PCT", "0.5")),
            proxy_url=os.environ.get("HTTP_PROXY") or os.environ.get("HTTPS_PROXY"),
            ibkr_enabled=bool(os.environ.get("IBKR_API_TOKEN")),
        )


# Platform display names keyed by internal source id
PLATFORM_LABELS: dict[str, str] = {
    "draftkings": "DraftKings Sportsbook (NC)",
    "fanduel": "FanDuel Sportsbook (NC)",
    "betmgm": "BetMGM Sportsbook (NC)",
    "kalshi": "Kalshi",
    "predictit": "PredictIt",
    "forecastex": "ForecastEx",
}
