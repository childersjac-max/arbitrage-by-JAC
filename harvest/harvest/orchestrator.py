"""Multi-threaded harvest orchestrator with layered fallback."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Iterable

from harvest.config import HarvestConfig, configured_sources
from harvest.extractors.base import BaseExtractor
from harvest.extractors.betfair import BetfairExtractor
from harvest.extractors.kalshi import KalshiExtractor, attach_kalshi_to_sportsbook_fragments
from harvest.extractors.optic_odds import OpticOddsExtractor
from harvest.extractors.polymarket import PolymarketExtractor
from harvest.extractors.stubs import (
    DraftKingsPredictionsExtractor,
    FanDuelPredictsExtractor,
    SmarketsExtractor,
    SportXExtractor,
)
from harvest.models import MarketFragment, UnifiedArbitrageRow
from harvest.normalize import normalize_board
from harvest.splice import splice_fragments

logger = logging.getLogger(__name__)


class HarvestOrchestrator:
    def __init__(self, cfg: HarvestConfig | None = None) -> None:
        self.cfg = cfg or HarvestConfig.from_env()
        self._extractors = self._build_extractors()

    def _build_extractors(self) -> list[BaseExtractor]:
        cfg = self.cfg
        extractors: list[BaseExtractor] = [
            OpticOddsExtractor(cfg),
            KalshiExtractor(cfg),
            PolymarketExtractor(cfg),
            BetfairExtractor(cfg),
            DraftKingsPredictionsExtractor(cfg),
            FanDuelPredictsExtractor(cfg),
            SmarketsExtractor(cfg),
            SportXExtractor(cfg),
        ]
        return [e for e in extractors if e.is_configured or e.source_id in ("kalshi", "polymarket")]

    def run(self) -> list[UnifiedArbitrageRow]:
        fragments = self.collect_fragments()
        board = splice_fragments(fragments)
        return normalize_board(board)

    def collect_fragments(self) -> list[MarketFragment]:
        active = [e for e in self._extractors if self._should_run(e)]
        logger.info(
            "Harvest starting: %s configured sources",
            configured_sources(self.cfg),
        )

        results: list[MarketFragment] = []
        with ThreadPoolExecutor(max_workers=self.cfg.max_workers) as pool:
            futures = {pool.submit(self._safe_fetch, ext): ext for ext in active}
            for fut in as_completed(futures):
                ext = futures[fut]
                try:
                    batch = fut.result()
                    logger.info("%s returned %d fragments", ext.source_id, len(batch))
                    results.extend(batch)
                except Exception:
                    logger.exception("Extractor failed: %s", ext.source_id)

        optic = [r for r in results if r.platform_kind.value == "sportsbook"]
        kalshi = [r for r in results if r.source == "kalshi"]
        if optic and kalshi:
            results = [r for r in results if r.source != "kalshi"]
            results.extend(
                attach_kalshi_to_sportsbook_fragments(
                    optic, kalshi, threshold=self.cfg.fuzzy_match_threshold
                )
            )
        return results

    def _should_run(self, ext: BaseExtractor) -> bool:
        if ext.source_id == "optic_odds":
            return ext.is_configured and self.cfg.enable_optic
        if ext.source_id == "kalshi":
            return self.cfg.enable_kalshi
        if ext.source_id == "polymarket":
            return self.cfg.enable_polymarket
        if ext.source_id == "betfair_exchange":
            return self.cfg.enable_betfair and ext.is_configured
        return ext.is_configured

    @staticmethod
    def _safe_fetch(ext: BaseExtractor) -> list[MarketFragment]:
        try:
            return ext.fetch()
        except Exception:
            logger.exception("fetch() error for %s", ext.source_id)
            return []
