"""
Orchestration loop — runs all NC profiles concurrently (sync), splices, normalizes, emits arbs.
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
from .profiles import NC_PROFILES

logger = logging.getLogger(__name__)


class NCOrchestrator:
    def __init__(self, config: CollectorConfig | None = None):
        self.config = config or CollectorConfig.from_env()
        self.http = ResilientHttpClient(self.config)
        self.profiles = [cls(self.config, self.http) for cls in NC_PROFILES]
        self.splice = SpliceEngine()
        self.arb = ArbitragePipeline(min_yield_pct=self.config.min_arb_yield_pct)

    def run_once(self) -> dict[str, Any]:
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
