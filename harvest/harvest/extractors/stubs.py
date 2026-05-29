"""
Placeholders for sources that require partner / exchange API credentials.

DraftKings Predictions, FanDuel Predicts, Smarkets, SportX — enable when keys exist.
Do not scrape consumer sites; register for official market data access.
"""

from __future__ import annotations

from harvest.config import HarvestConfig
from harvest.extractors.base import BaseExtractor, FetchLayer
from harvest.models import MarketFragment


class _StubExtractor(BaseExtractor):
    layer = FetchLayer.DISABLED

    def __init__(self, cfg: HarvestConfig, source_id: str, env_hint: str) -> None:
        self._cfg = cfg
        self.source_id = source_id
        self._env_hint = env_hint

    @property
    def is_configured(self) -> bool:
        return False

    def fetch(self) -> list[MarketFragment]:
        return []


class DraftKingsPredictionsExtractor(_StubExtractor):
    def __init__(self, cfg: HarvestConfig) -> None:
        super().__init__(cfg, "draftkings_predictions", "DK_PREDICTIONS_API_KEY")


class FanDuelPredictsExtractor(_StubExtractor):
    def __init__(self, cfg: HarvestConfig) -> None:
        super().__init__(cfg, "fanduel_predicts", "FANDUEL_PREDICTS_API_KEY")


class SmarketsExtractor(_StubExtractor):
    def __init__(self, cfg: HarvestConfig) -> None:
        super().__init__(cfg, "smarkets", "SMARKETS_API_KEY")


class SportXExtractor(_StubExtractor):
    def __init__(self, cfg: HarvestConfig) -> None:
        super().__init__(cfg, "sportx", "SPORTX_API_KEY")
