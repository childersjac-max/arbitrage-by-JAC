"""PredictIt + ForecastEx combined prediction-market profile."""

from __future__ import annotations

from ..models import MarketPacket
from ..sources.forecastex import ForecastExSource
from ..sources.predictit import PredictItSource
from .base import ExtractionProfile


class PredictionMarketsProfile(ExtractionProfile):
    """
    Profile #5: regulated prediction/event contracts (PredictIt primary,
    ForecastEx CSV fallback when IBKR is not configured).
    """

    platform_key = "prediction_markets"
    display_name = "PredictIt / ForecastEx"

    def __init__(self, config, http):
        super().__init__(config, http)
        self._predictit = PredictItSource(config, http)
        self._forecastex = ForecastExSource(config, http)

    def extract(self, sport_keys: tuple[str, ...] | None = None) -> list[MarketPacket]:
        packets: list[MarketPacket] = []
        pi_markets = self._predictit.fetch_all()
        packets.extend(self._predictit.to_packets(pi_markets))
        packets.extend(self._forecastex.try_fetch_latest_prices())
        return packets
