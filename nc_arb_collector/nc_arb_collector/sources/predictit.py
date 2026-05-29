"""PredictIt public read-only marketdata API (1 req/sec)."""

from __future__ import annotations

import re
import time
from typing import Any

from ..config import CollectorConfig
from ..http.client import ResilientHttpClient
from ..models import MarketPacket, OddsLeg
from ..utils.odds_math import predictit_price_to_american


class PredictItSource:
    MIN_INTERVAL = 1.05

    def __init__(self, config: CollectorConfig, http: ResilientHttpClient):
        self.config = config
        self.http = http
        self._last_at = [0.0]

    def fetch_all(self) -> list[dict[str, Any]]:
        url = f"{self.config.predictit_base_url}/all/"
        data = self.http.get_json(
            url,
            min_interval_sec=self.MIN_INTERVAL,
            last_request_at=self._last_at,
        )
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("markets") or []
        return []

    def to_packets(self, markets: list[dict[str, Any]]) -> list[MarketPacket]:
        packets: list[MarketPacket] = []
        sports_re = re.compile(
            r"\b(nfl|nba|mlb|nhl|ncaa|college|football|basketball|baseball|hockey|"
            r"super bowl|world series|stanley cup|championship|playoff|mvp|"
            r"heisman|draft|ufc|mma|soccer|premier league|world cup|golf|pga|"
            r"tennis|wimbledon|masters|olympics|sports)\b",
            re.I,
        )
        for market in markets:
            name = market.get("name") or ""
            if not sports_re.search(name):
                continue
            for contract in market.get("contracts") or []:
                cname = contract.get("name") or ""
                price = contract.get("bestBuyYesCost") or contract.get("lastTradePrice")
                if price is None:
                    continue
                american = predictit_price_to_american(float(price))
                event_key = f"predictit:{market.get('id')}:{contract.get('id')}"
                packets.append(
                    MarketPacket(
                        source_platform="predictit",
                        event_key=event_key,
                        home_team=cname,
                        away_team=name,
                        market_type="h2h",
                        commence_time=market.get("timeStamp"),
                        legs=[
                            OddsLeg(
                                platform="predictit",
                                outcome_key=cname,
                                american_odds=american,
                                raw=contract,
                            )
                        ],
                        metadata={"market_name": name},
                    )
                )
        return packets
