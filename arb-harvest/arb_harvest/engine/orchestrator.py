"""Central orchestrator: baseline + supplemental + arbitrage JSON."""

from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable

from arb_harvest.baseline import TheOddsApiBaseline
from arb_harvest.config import HarvestConfig
from arb_harvest.engine.arbitrage import detect_arbitrage
from arb_harvest.engine.merger import fetch_supplemental_parallel, splice_events
from arb_harvest.models import ArbitrageSignal, NormalizedEvent, utc_now_iso
from arb_harvest.net import PoliteHttpClient
from arb_harvest.normalize import EventMatcher
from arb_harvest.scrape import build_fetchers


class HarvestOrchestrator:
    def __init__(self, config: HarvestConfig | None = None):
        self.config = config or HarvestConfig.from_env()
        self.http = PoliteHttpClient(requests_per_second=self.config.http_rps)
        self.baseline = TheOddsApiBaseline(self.config, self.http)
        self.fetchers = build_fetchers(self.config, self.http)
        self.matcher = EventMatcher()

    def run_once(self) -> dict[str, Any]:
        """Single harvest cycle → unified JSON payload."""
        baseline_events: list[NormalizedEvent] = []

        # Layer A: The Odds API (parallel per sport)
        with ThreadPoolExecutor(max_workers=self.config.max_workers) as pool:
            sport_futures = {
                pool.submit(self.baseline.fetch_sport_odds, sport): sport
                for sport in self.config.sport_keys
            }
            raw_by_sport: dict[str, list] = {}
            for fut in as_completed(sport_futures):
                sport = sport_futures[fut]
                raw_by_sport[sport] = fut.result() or []

        for sport, raw in raw_by_sport.items():
            baseline_events.extend(self.baseline.events_to_normalized(raw, sport))

        if self.config.enable_event_props:
            baseline_events = self.baseline.enrich_with_event_props(baseline_events)

        # Supplemental public APIs (Kalshi, Polymarket, …)
        supplemental = fetch_supplemental_parallel(
            self.fetchers, max_workers=self.config.max_workers
        )
        merged = splice_events(baseline_events, supplemental, self.matcher)
        signals = detect_arbitrage(merged, self.config.min_arb_yield_pct)

        return self._build_payload(merged, signals)

    def _build_payload(
        self,
        events: list[NormalizedEvent],
        signals: list[ArbitrageSignal],
    ) -> dict[str, Any]:
        return {
            "timestamp": utc_now_iso(),
            "event_count": len(events),
            "arbitrage_opportunity_count": len(signals),
            "events": [
                {
                    "normalized_event_name": e.normalized_name,
                    "sport_key": e.sport_key,
                    "commence_time": e.commence_time,
                    "home_team": e.home_team,
                    "away_team": e.away_team,
                    "sources": [
                        {
                            "source_id": b.source_id,
                            "title": b.title,
                            "markets": [
                                {
                                    "market_type": m.key,
                                    "outcomes": [
                                        {
                                            "name": o.name,
                                            "price_american": o.price_american,
                                            "point": o.point,
                                            "volume": o.volume,
                                        }
                                        for o in m.outcomes
                                    ],
                                }
                                for m in b.markets
                            ],
                        }
                        for b in e.books
                    ],
                }
                for e in events
            ],
            "arbitrage_signals": [s.to_dict() for s in signals],
        }

    def run_loop(
        self,
        *,
        on_payload: Callable[[dict[str, Any]], None] | None = None,
        max_iterations: int | None = None,
    ) -> None:
        n = 0
        while max_iterations is None or n < max_iterations:
            payload = self.run_once()
            if on_payload:
                on_payload(payload)
            else:
                print(json.dumps(payload, indent=2)[:8000])
            n += 1
            time.sleep(self.config.poll_interval_sec)
