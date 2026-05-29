"""
Betfair Exchange — official API (requires developer app key + session).

Docs: https://docs.developer.betfair.com/
Layer A: listMarketCatalogue + listMarketBook via JSON-RPC.
"""

from __future__ import annotations

import httpx

from dataclasses import replace

from harvest.config import HarvestConfig
from harvest.extractors.base import BaseExtractor, FetchLayer
from harvest.models import MarketFragment, MarketType, PlatformKind, PriceQuote
from harvest.resilience import request_json

BETFAIR_EXCHANGE = "https://api.betfair.com/exchange/betting/json-rpc/v1"


class BetfairExtractor(BaseExtractor):
    source_id = "betfair_exchange"
    layer = FetchLayer.A_HTTP_API

    def __init__(self, cfg: HarvestConfig) -> None:
        self._cfg = cfg

    @property
    def is_configured(self) -> bool:
        return bool(self._cfg.betfair_app_key and self._cfg.betfair_session_token)

    def fetch(self) -> list[MarketFragment]:
        if not self.is_configured:
            return []

        headers = {
            "X-Application": self._cfg.betfair_app_key or "",
            "X-Authentication": self._cfg.betfair_session_token or "",
            "Content-Type": "application/json",
        }
        payload = {
            "jsonrpc": "2.0",
            "method": "SportsAPING/v1.0/listMarketCatalogue",
            "params": {
                "filter": {"eventTypeIds": ["1"], "marketTypeCodes": ["MATCH_ODDS"]},
                "maxResults": 50,
                "marketProjection": ["RUNNER_DESCRIPTION", "EVENT"],
            },
            "id": 1,
        }

        with httpx.Client(timeout=self._cfg.request_timeout_s) as client:
            cat = request_json(client, "POST", BETFAIR_EXCHANGE, headers=headers, json=payload)

        fragments: list[MarketFragment] = []
        for mc in cat.get("result", []):
            event = mc.get("event", {})
            name = event.get("name", "")
            if " v " not in name and " @ " not in name:
                continue
            parts = name.replace(" v ", " vs ").split(" vs ")
            if len(parts) != 2:
                continue
            home, away = parts[0].strip(), parts[1].strip()
            market_id = mc.get("marketId")
            fragments.append(
                MarketFragment(
                    source="betfair_exchange",
                    platform_kind=PlatformKind.EXCHANGE,
                    sport="soccer",
                    league=None,
                    home_team=home,
                    away_team=away,
                    commence_time=mc.get("marketStartTime"),
                    market_type=MarketType.BACK_LAY,
                    market_key=market_id or name,
                    quotes=[],
                    metadata={"market_id": market_id, "layer": self.layer.value},
                )
            )
        return self._enrich_books(fragments, headers)

    def _enrich_books(
        self, fragments: list[MarketFragment], headers: dict
    ) -> list[MarketFragment]:
        ids = [f.metadata.get("market_id") for f in fragments if f.metadata.get("market_id")]
        if not ids:
            return fragments

        payload = {
            "jsonrpc": "2.0",
            "method": "SportsAPING/v1.0/listMarketBook",
            "params": {"marketIds": ids[:20], "priceProjection": {"priceData": ["EX_BEST_OFFERS"]}},
            "id": 2,
        }
        with httpx.Client(timeout=self._cfg.request_timeout_s) as client:
            books = request_json(
                client, "POST", BETFAIR_EXCHANGE, headers=headers, json=payload
            )

        book_by_id = {b["marketId"]: b for b in books.get("result", [])}
        enriched: list[MarketFragment] = []
        for frag in fragments:
            mid = frag.metadata.get("market_id")
            book = book_by_id.get(mid)
            if not book:
                enriched.append(frag)
                continue
            quotes: list[PriceQuote] = []
            for runner in book.get("runners", []):
                name = str(runner.get("selectionId"))
                back = (runner.get("ex") or {}).get("availableToBack") or []
                if back:
                    decimal_odds = float(back[0]["price"])
                    quotes.append(
                        PriceQuote(
                            platform="betfair_exchange",
                            outcome_label=name,
                            decimal_odds=decimal_odds,
                            liquidity_volume=float(back[0].get("size", 0)),
                            raw=runner,
                        )
                    )
            enriched.append(replace(frag, quotes=quotes or frag.quotes))
        return enriched
