"""
Catalog of FREE data sources — no Optic Odds / OddsJam required.

The only paid integration is The Odds API (user subscription) for NC sportsbooks.
"""

from __future__ import annotations

FREE_SOURCES: dict[str, dict[str, str]] = {
    "kalshi": {
        "cost": "free",
        "base_url": "https://api.elections.kalshi.com/trade-api/v2",
        "docs": "https://docs.kalshi.com",
        "auth": "none (public market data)",
    },
    "predictit": {
        "cost": "free",
        "base_url": "https://www.predictit.org/api/marketdata",
        "docs": "https://www.predictit.org/api/marketdata/all/",
        "auth": "none (read-only, 1 req/sec)",
    },
    "forecastex": {
        "cost": "free",
        "base_url": "https://www.forecastex.com/api/download",
        "docs": "https://www.forecastex.com/data",
        "auth": "none (CSV pairs/prices/summary)",
    },
    "polymarket": {
        "cost": "free",
        "base_url": "https://gamma-api.polymarket.com",
        "docs": "https://docs.polymarket.com",
        "auth": "none (Gamma API)",
    },
}

PAID_SOURCES: dict[str, dict[str, str]] = {
    "the_odds_api": {
        "cost": "subscription",
        "base_url": "https://api.the-odds-api.com/v4",
        "env_key": "ODDS_API_KEY",
        "covers": "draftkings, fanduel, betmgm (and other US books)",
    },
}
