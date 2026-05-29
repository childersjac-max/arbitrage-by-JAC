"""
ForecastEx free CSV downloads via /api/download (no IBKR required).

Pairs CSV refreshes ~every 10 minutes; prices/summary are daily after market close.
"""

from __future__ import annotations

import csv
import io
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from ..config import CollectorConfig
from ..http.client import ResilientHttpClient
from ..models import MarketPacket, OddsLeg
from ..utils.odds_math import predictit_price_to_american


class ForecastExSource:
    # Free CSV uses coded contracts (e.g. UHLAX_051126_70) — date+strike suffix pattern
    TRADABLE_CONTRACT = re.compile(r"_\d{6}[_\d.]+", re.I)
    SPORTS_RE = re.compile(
        r"\b(nfl|nba|mlb|nhl|vs\.?|champion|winner|playoff|game|spread|total|"
        r"touchdown|points|rebounds|ufc|mma|golf|pga|soccer|mls|ncaa)\b",
        re.I,
    )

    def __init__(self, config: CollectorConfig, http: ResilientHttpClient):
        self.config = config
        self.http = http
        self.download_base = "https://www.forecastex.com/api/download"

    def _download_csv(self, file_type: str, date_yyyymmdd: str) -> str | None:
        url = f"{self.download_base}?type={file_type}&date={date_yyyymmdd}"
        if self.config.use_curl_cffi:
            try:
                from curl_cffi import requests as cffi_requests

                r = cffi_requests.get(url, timeout=self.config.request_timeout_sec, impersonate="chrome131")
                if r.status_code == 200 and "," in r.text[:300]:
                    return r.text
            except Exception:
                pass
        resp = self.http._httpx.get(url)
        if resp.status_code == 200 and "," in resp.text[:300]:
            return resp.text
        return None

    def fetch_latest_pairs_csv(self, lookback_days: int = 3) -> str | None:
        """Try recent dates until pairs CSV is found."""
        today = datetime.now(timezone.utc).date()
        for delta in range(lookback_days):
            d = today - timedelta(days=delta)
            yyyymmdd = d.strftime("%Y%m%d")
            text = self._download_csv("pairs", yyyymmdd)
            if text:
                return text
        return None

    def fetch_packets_from_pairs_csv(self, csv_text: str) -> list[MarketPacket]:
        packets: list[MarketPacket] = []
        reader = csv.DictReader(io.StringIO(csv_text))
        for row in reader:
            contract = (
                row.get("event_contract")
                or row.get("Event")
                or row.get("contract")
                or ""
            )
            if not contract:
                continue
            try:
                qty = int(float(row.get("quantity") or 0))
            except ValueError:
                qty = 0
            if qty <= 0:
                continue
            if not (self.SPORTS_RE.search(contract) or self.TRADABLE_CONTRACT.search(contract)):
                continue
            try:
                yes_p = float(row.get("yes_price") or row.get("yes") or 0)
            except ValueError:
                continue
            if yes_p <= 0 or yes_p >= 1:
                continue
            american = predictit_price_to_american(yes_p)
            event_key = f"forecastex:{contract}"
            packets.append(
                MarketPacket(
                    source_platform="forecastex",
                    event_key=event_key,
                    home_team=contract,
                    away_team="",
                    market_type="h2h",
                    commence_time=row.get("pair_time") or row.get("expiration_date"),
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

    def try_fetch_packets(self) -> list[MarketPacket]:
        csv_text = self.fetch_latest_pairs_csv()
        if not csv_text:
            return []
        return self.fetch_packets_from_pairs_csv(csv_text)
