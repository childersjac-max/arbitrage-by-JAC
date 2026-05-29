"""Free prediction markets: PredictIt + ForecastEx + Polymarket (no paid API)."""

from __future__ import annotations

from ..models import MarketPacket
from ..sources.forecastex import ForecastExSource
from ..sources.polymarket import PolymarketSource
from ..sources.predictit import PredictItSource
from .base import ExtractionProfile


class PredictionMarketsProfile(ExtractionProfile):
    platform_key = "prediction_markets"
    display_name = "PredictIt / ForecastEx / Polymarket"

    def __init__(self, config, http):
        super().__init__(config, http)
        self._predictit = PredictItSource(config, http)
        self._forecastex = ForecastExSource(config, http)
        self._polymarket = PolymarketSource(config, http)

    def extract(self, sport_keys: tuple[str, ...] | None = None) -> list[MarketPacket]:
        packets: list[MarketPacket] = []
        packets.extend(self._predictit.to_packets(self._predictit.fetch_all()))
        packets.extend(self._forecastex.try_fetch_packets())
        pm_events = self._polymarket.fetch_sports_events()
        packets.extend(self._polymarket.to_packets(pm_events))
        return packets
