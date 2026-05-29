"""
Polymarket — public Gamma + CLOB APIs (no auth for read-only).

Gamma: https://gamma-api.polymarket.com/markets
CLOB book: https://clob.polymarket.com/book?token_id=
"""

from __future__ import annotations

import httpx

from harvest.config import HarvestConfig
from harvest.extractors.base import BaseExtractor, FetchLayer
from harvest.models import MarketFragment, MarketType, PlatformKind, PriceQuote
from harvest.odds_math import prob_cents_to_american
from harvest.resilience import request_json

GAMMA_BASE = "https://gamma-api.polymarket.com"
CLOB_BASE = "https://clob.polymarket.com"


class PolymarketExtractor(BaseExtractor):
    source_id = "polymarket"
    layer = FetchLayer.A_HTTP_API

    def __init__(self, cfg: HarvestConfig) -> None:
        self._cfg = cfg

    def fetch(self) -> list[MarketFragment]:
        with httpx.Client(timeout=self._cfg.request_timeout_s) as client:
            body = request_json(
                client,
                "GET",
                f"{GAMMA_BASE}/markets",
                params={"active": "true", "closed": "false", "limit": 100},
            )

        markets = body if isinstance(body, list) else body.get("data", body)
        if not isinstance(markets, list):
            markets = []

        fragments: list[MarketFragment] = []
        for m in markets:
            question = (m.get("question") or m.get("title") or "").strip()
            if not question:
                continue
            lower = question.lower()
            if " vs " not in lower and " beat " not in lower:
                continue

            yes_price = self._yes_price(m)
            if yes_price is None:
                continue

            # Gamma returns 0–1 probability or cents depending on field
            if yes_price <= 1:
                cents = yes_price * 100
            else:
                cents = yes_price

            american = prob_cents_to_american(cents)
            home, away = self._parse_teams(question)
            liquidity = m.get("liquidity") or m.get("volume")
            fragments.append(
                MarketFragment(
                    source="polymarket",
                    platform_kind=PlatformKind.PREDICTION_MARKET,
                    sport="unknown",
                    league=None,
                    home_team=home,
                    away_team=away,
                    commence_time=m.get("endDate") or m.get("end_date_iso"),
                    market_type=MarketType.YES_NO,
                    market_key=str(m.get("conditionId") or m.get("id") or question),
                    quotes=[
                        PriceQuote(
                            platform="polymarket",
                            outcome_label=question,
                            american_odds=american,
                            implied_prob=cents / 100.0,
                            liquidity_volume=float(liquidity) if liquidity else None,
                            raw=m,
                        )
                    ],
                    metadata={"layer": self.layer.value},
                )
            )
        return fragments

    def _yes_price(self, market: dict) -> float | None:
        for key in ("outcomePrices", "outcome_prices", "bestBid", "best_ask"):
            if key in market and market[key]:
                val = market[key]
                if isinstance(val, str):
                    import json

                    try:
                        val = json.loads(val)
                    except json.JSONDecodeError:
                        continue
                if isinstance(val, list) and val:
                    try:
                        return float(val[0])
                    except (TypeError, ValueError):
                        pass
        if market.get("lastTradePrice") is not None:
            return float(market["lastTradePrice"])
        return None

    @staticmethod
    def _parse_teams(question: str) -> tuple[str, str]:
        lower = question.lower()
        for sep in (" vs. ", " vs ", " beat "):
            if sep in lower:
                idx = lower.index(sep)
                a = question[:idx].strip()
                b = question[idx + len(sep) :].strip()
                return a[:60], b[:60]
        return "TBD", question[:60]
