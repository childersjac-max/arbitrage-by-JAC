"""Register supplemental fetchers (public APIs only)."""

from __future__ import annotations

from arb_harvest.config import HarvestConfig
from arb_harvest.net import PoliteHttpClient
from arb_harvest.scrape.base import SupplementalFetcher
from arb_harvest.scrape.betfair import BetfairFetcher
from arb_harvest.scrape.kalshi import KalshiFetcher
from arb_harvest.scrape.polymarket import PolymarketFetcher
from arb_harvest.scrape.sx_bet import SxBetFetcher

# Platforms covered by The Odds API baseline (no separate scraper):
# DraftKings, FanDuel, BetMGM, Caesars, Fanatics, bet365, ESPN Bet / The Score
#
# Platforms requiring official credentials (extend with your own adapters):
# - Betfair Exchange: https://docs.developer.betfair.com/
# - Smarkets: https://docs.smarkets.com/
# - SportX / SX Bet: https://docs.sx.bet/
# - DraftKings Predictions / FanDuel Prediction: use operator APIs where licensed


def build_fetchers(config: HarvestConfig, http: PoliteHttpClient) -> list[SupplementalFetcher]:
    fetchers: list[SupplementalFetcher] = []
    if config.enable_kalshi:
        fetchers.append(KalshiFetcher(http))
    if config.enable_polymarket:
        fetchers.append(PolymarketFetcher(http))
    if config.enable_sx_bet:
        fetchers.append(SxBetFetcher(http))
    if config.enable_betfair:
        fetchers.append(BetfairFetcher(http))
    return fetchers
