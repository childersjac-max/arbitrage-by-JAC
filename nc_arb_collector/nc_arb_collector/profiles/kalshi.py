from ..sources.kalshi import KalshiSource
from .base import ExtractionProfile


class KalshiProfile(ExtractionProfile):
    platform_key = "kalshi"
    display_name = "Kalshi"

    def __init__(self, config, http):
        super().__init__(config, http)
        self._source = KalshiSource(config, http)

    def extract(self, sport_keys: tuple[str, ...] | None = None) -> list:
        markets = self._source.fetch_open_markets()
        return self._source.to_packets(markets)
