"""
Orchestration loop — runs all NC profiles concurrently, splices, normalizes, emits arbs.

Paid: The Odds API only (one request per sport for DK+FD+BetMGM).
Free: Kalshi, PredictIt, ForecastEx CSV, Polymarket Gamma API.
"""

from __future__ import annotations

import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from .config import CollectorConfig
from .engine.arbitrage import ArbitragePipeline
from .engine.splice import SpliceEngine
from .http.client import ResilientHttpClient
from .profiles import (
    BetMGMProfile,
    DraftKingsProfile,
    FanDuelProfile,
    KalshiProfile,
    PredictionMarketsProfile,
)
from .profiles.base import ExtractionProfile
from .sources.free_registry import FREE_SOURCES, PAID_SOURCES
from .sources.sportsbook_cache import SportsbookCache
from .sources.the_odds_api import TheOddsApiSource

logger = logging.getLogger(__name__)


class NCOrchestrator:
    def __init__(self, config: CollectorConfig | None = None):
        self.config = config or CollectorConfig.from_env()
        self.http = ResilientHttpClient(self.config)
        self._odds_api = TheOddsApiSource(self.config, self.http)
        self._sportsbook_cache = SportsbookCache(self.config, self._odds_api)
        self.profiles: list[ExtractionProfile] = self._build_profiles()
        self.splice = SpliceEngine()
        self.arb = ArbitragePipeline(min_yield_pct=self.config.min_arb_yield_pct)

    def _build_profiles(self) -> list[ExtractionProfile]:
        cache = self._sportsbook_cache
        return [
            DraftKingsProfile(self.config, self.http, cache=cache),
            FanDuelProfile(self.config, self.http, cache=cache),
            BetMGMProfile(self.config, self.http, cache=cache),
            KalshiProfile(self.config, self.http),
            PredictionMarketsProfile(self.config, self.http),
        ]

    def run_once(self) -> dict[str, Any]:
        if self._odds_api.enabled:
            self._sportsbook_cache.prefetch()
            logger.info(
                "The Odds API: %s sport fetches (%s books each)",
                self._sportsbook_cache.api_calls_made,
                "draftkings,fanduel,betmgm",
            )
        else:
            logger.warning(
                "ODDS_API_KEY not set — sportsbook profiles empty. "
                "Free sources (Kalshi, PredictIt, ForecastEx, Polymarket) still run."
            )

        all_packets = []
        profile_stats: dict[str, int] = {}

        def _run_profile(profile):
            try:
                return profile.platform_key, profile.extract()
            except Exception as e:
                logger.warning("Profile %s failed: %s", profile.platform_key, e)
                return profile.platform_key, []

        with ThreadPoolExecutor(max_workers=len(self.profiles)) as pool:
            futures = {pool.submit(_run_profile, p): p for p in self.profiles}
            for fut in as_completed(futures):
                key, packets = fut.result()
                profile_stats[key] = len(packets)
                all_packets.extend(packets)

        self.splice = SpliceEngine()
        self.splice.ingest_packets(all_packets)
        unified = self.splice.unified_markets()
        arb_rows = self.arb.scan(unified)

        return {
            "data_sources": {
                "paid": PAID_SOURCES,
                "free": FREE_SOURCES,
                "odds_api_configured": self._odds_api.enabled,
                "odds_api_requests_this_cycle": self._sportsbook_cache.api_calls_made,
            },
            "profile_packet_counts": profile_stats,
            "splice_stats": self.splice.gap_fill_report(),
            "board": self.splice.snapshot(),
            "arbitrage": self.arb.to_json(arb_rows),
        }

    def run_loop(self, iterations: int | None = None) -> None:
        n = 0
        while iterations is None or n < iterations:
            result = self.run_once()
            print(json.dumps(result["arbitrage"], indent=2))
            logger.info(
                "cycle=%s arbs=%s splice=%s",
                n,
                result["arbitrage"]["count"],
                result["splice_stats"],
            )
            n += 1
            if iterations is not None and n >= iterations:
                break
            time.sleep(self.config.poll_interval_sec)

    def close(self) -> None:
        self.http.close()
