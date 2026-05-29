"""
Betfair Exchange — official Exchange API (JSON-RPC + SSO login).

Requires env:
  BETFAIR_APP_KEY
  BETFAIR_USERNAME
  BETFAIR_PASSWORD

Docs: https://docs.developer.betfair.com/
"""

from __future__ import annotations

import os
from typing import Any

import requests

from arb_harvest.models import MarketQuote, NormalizedEvent, OutcomeQuote, SourceBook
from arb_harvest.net import PoliteHttpClient
from arb_harvest.normalize.sport_infer import infer_sport_key
from arb_harvest.scrape.base import SupplementalFetcher

SSO_URL = "https://identitysso.betfair.com/api/login"
BETTING_URL = "https://api.betfair.com/exchange/betting/json-rpc/v1"

# Betfair event type IDs
_EVENT_TYPES = {
    "basketball_nba": "7522",
    "americanfootball_nfl": "6423",
    "icehockey_nhl": "7524",
    "baseball_mlb": "7511",
}


def _decimal_to_american(d: float) -> int:
    if d <= 1:
        return 100
    if d >= 2.0:
        return int(round((d - 1) * 100))
    return int(round(-100 / (d - 1)))


class BetfairFetcher(SupplementalFetcher):
    source_id = "betfair_ex_uk"

    def __init__(self, http: PoliteHttpClient):
        self.http = http
        self.app_key = os.environ.get("BETFAIR_APP_KEY", "").strip()
        self.username = os.environ.get("BETFAIR_USERNAME", "").strip()
        self.password = os.environ.get("BETFAIR_PASSWORD", "").strip()
        self._session: str | None = None

    def _enabled(self) -> bool:
        return bool(self.app_key and self.username and self.password)

    def _login(self) -> bool:
        if self._session:
            return True
        try:
            r = requests.post(
                SSO_URL,
                headers={"X-Application": self.app_key, "Accept": "application/json"},
                data={"username": self.username, "password": self.password},
                timeout=20,
            )
            if r.status_code != 200:
                return False
            body = r.json()
            token = body.get("token") or body.get("sessionToken")
            if not token:
                return False
            self._session = str(token)
            return True
        except requests.RequestException:
            return False

    def _rpc(self, method: str, params: dict[str, Any]) -> Any:
        if not self._login():
            return None
        payload = {"jsonrpc": "2.0", "method": method, "params": params, "id": 1}
        try:
            r = requests.post(
                BETTING_URL,
                json=payload,
                headers={
                    "X-Application": self.app_key,
                    "X-Authentication": self._session or "",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                timeout=25,
            )
            if r.status_code != 200:
                return None
            data = r.json()
            if "error" in data:
                return None
            return data.get("result")
        except requests.RequestException:
            return None

    def fetch(self) -> list[NormalizedEvent]:
        if not self._enabled():
            return []

        events: list[NormalizedEvent] = []
        for sport_key, event_type_id in _EVENT_TYPES.items():
            catalogue = self._rpc(
                "SportsAPING/v1.0/listMarketCatalogue",
                {
                    "filter": {
                        "eventTypeIds": [event_type_id],
                        "marketTypeCodes": ["MATCH_ODDS"],
                        "marketCountries": ["US", "GB"],
                    },
                    "maxResults": "40",
                    "marketProjection": ["RUNNER_DESCRIPTION", "EVENT", "MARKET_START_TIME"],
                },
            )
            if not catalogue:
                continue
            market_ids = [c["marketId"] for c in catalogue if c.get("marketId")]
            if not market_ids:
                continue
            books = self._rpc(
                "SportsAPING/v1.0/listMarketBook",
                {
                    "marketIds": market_ids[:20],
                    "priceProjection": {"priceData": ["EX_BEST_OFFERS"], "virtualise": False},
                },
            )
            if not books:
                continue
            cat_by_id = {c["marketId"]: c for c in catalogue}

            for book in books:
                mid = book.get("marketId")
                cat = cat_by_id.get(mid) or {}
                runners_cat = {r["selectionId"]: r for r in (cat.get("runners") or [])}
                event_name = (cat.get("event") or {}).get("name") or ""
                if " v " in event_name:
                    parts = event_name.split(" v ", 1)
                elif " @ " in event_name:
                    parts = event_name.split(" @ ", 1)
                else:
                    continue
                home_raw, away_raw = parts[0].strip(), parts[1].strip()
                outcomes: list[OutcomeQuote] = []
                total_vol = 0.0
                for runner in book.get("runners") or []:
                    sid = runner.get("selectionId")
                    rc = runners_cat.get(sid) or {}
                    name = rc.get("runnerName") or str(sid)
                    ex = runner.get("ex") or {}
                    backs = ex.get("availableToBack") or []
                    if not backs:
                        continue
                    best = backs[0]
                    dec = float(best.get("price", 0))
                    size = float(best.get("size", 0))
                    total_vol += size
                    outcomes.append(
                        OutcomeQuote(
                            name=name,
                            price_american=_decimal_to_american(dec),
                            volume=size,
                        )
                    )
                if len(outcomes) < 2:
                    continue
                events.append(
                    NormalizedEvent(
                        event_id=str(mid),
                        sport_key=sport_key,
                        normalized_name="",
                        home_team=home_raw,
                        away_team=away_raw,
                        commence_time=cat.get("marketStartTime") or "",
                        books=[
                            SourceBook(
                                source_id=self.source_id,
                                title="Betfair Exchange",
                                markets=[MarketQuote(key="h2h", outcomes=outcomes)],
                                raw=book,
                            )
                        ],
                    )
                )
        return events
