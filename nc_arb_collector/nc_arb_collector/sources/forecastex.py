"""
ForecastEx data via public CSV portal (forecastex.com/data).

IBKR Web API can be wired when IBKR_API_TOKEN is set; this module parses
daily price CSVs as the zero-auth fallback.
"""

from __future__ import annotations

import csv
import io
import re
from datetime import datetime, timezone
from typing import Any

from ..config import CollectorConfig
from ..http.client import ResilientHttpClient
from ..models import MarketPacket, OddsLeg
from ..utils.odds_math import predictit_price_to_american


class ForecastExSource:
    """Loads latest prices CSV from ForecastEx data portal."""

    SPORTS_RE = re.compile(
        r"\b(nfl|nba|mlb|nhl|vs\.?|champion|winner|playoff)\b",
        re.I,
    )

    def __init__(self, config: CollectorConfig, http: ResilientHttpClient):
        self.config = config
        self.http = http

    def fetch_packets_from_csv(self, csv_text: str) -> list[MarketPacket]:
        packets: list[MarketPacket] = []
        reader = csv.DictReader(io.StringIO(csv_text))
        for row in reader:
            label = (
                row.get("Event")
                or row.get("event")
                or row.get("Contract")
                or row.get("contract")
                or row.get("Description")
                or ""
            )
            if not label or not self.SPORTS_RE.search(label):
                continue
            price_raw = (
                row.get("Close")
                or row.get("close")
                or row.get("Price")
                or row.get("price")
                or row.get("Last")
            )
            if price_raw is None:
                continue
            try:
                price = float(str(price_raw).replace("$", "").strip())
            except ValueError:
                continue
            if price > 1.0:
                price = price / 100.0
            american = predictit_price_to_american(price)
            event_key = f"forecastex:{label}"
            packets.append(
                MarketPacket(
                    source_platform="forecastex",
                    event_key=event_key,
                    home_team=label,
                    away_team="",
                    market_type="h2h",
                    commence_time=datetime.now(timezone.utc).isoformat(),
                    legs=[
                        OddsLeg(
                            platform="forecastex",
                            outcome_key="yes",
                            american_odds=american,
                            raw=dict(row),
                        )
                    ],
                )
            )
        return packets

    def try_fetch_latest_prices(self) -> list[MarketPacket]:
        """
        Attempt to pull today's prices CSV. Portal HTML structure may change;
        returns [] on failure so other sources still populate the board.
        """
        # Direct CSV URLs follow pattern on /data page; try recent date path
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        candidates = [
            f"{self.config.forecastex_data_base}/prices/{today}.csv",
            f"{self.config.forecastex_data_base}/Prices/{today}.csv",
        ]
        for url in candidates:
            if self.config.use_curl_cffi:
                try:
                    from curl_cffi import requests as cffi_requests

                    r = cffi_requests.get(url, timeout=self.config.request_timeout_sec, impersonate="chrome131")
                    if r.status_code == 200 and "," in r.text[:500]:
                        return self.fetch_packets_from_csv(r.text)
                except Exception:
                    pass
            resp = self.http._httpx.get(url)
            if resp.status_code == 200 and "," in resp.text[:500]:
                return self.fetch_packets_from_csv(resp.text)
        return []
