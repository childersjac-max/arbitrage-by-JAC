"""
Kalshi — regulated US prediction market (public trade API).

Endpoint: GET https://api.elections.kalshi.com/trade-api/v2/markets
"""

from __future__ import annotations

import httpx

from harvest.config import HarvestConfig
from harvest.extractors.base import BaseExtractor, FetchLayer
from harvest.fuzzy import match_event_titles
from harvest.models import MarketFragment, MarketType, PlatformKind, PriceQuote
from harvest.odds_math import prob_cents_to_american
from harvest.resilience import request_json

KALSHI_BASE = "https://api.elections.kalshi.com/trade-api/v2"


class KalshiExtractor(BaseExtractor):
    source_id = "kalshi"
    layer = FetchLayer.A_HTTP_API

    def __init__(self, cfg: HarvestConfig) -> None:
        self._cfg = cfg

    def fetch(self) -> list[MarketFragment]:
        with httpx.Client(timeout=self._cfg.request_timeout_s) as client:
            body = request_json(
                client,
                "GET",
                f"{KALSHI_BASE}/markets",
                params={"status": "open", "limit": 200},
                headers={"Accept": "application/json"},
            )

        fragments: list[MarketFragment] = []
        for m in body.get("markets", []):
            title = (m.get("title") or "").strip()
            lower = title.lower()
            if not title or (
                " vs " not in lower and " beat " not in lower and "winner" not in lower
            ):
                continue
            yes_cents = m.get("yes_ask") or m.get("yes_bid")
            if yes_cents is None:
                continue
            american = prob_cents_to_american(float(yes_cents))
            home, away = self._parse_teams(title)
            fragments.append(
                MarketFragment(
                    source="kalshi",
                    platform_kind=PlatformKind.PREDICTION_MARKET,
                    sport="unknown",
                    league=None,
                    home_team=home,
                    away_team=away,
                    commence_time=m.get("close_time"),
                    market_type=MarketType.YES_NO,
                    market_key=m.get("ticker", title),
                    quotes=[
                        PriceQuote(
                            platform="kalshi",
                            outcome_label=title,
                            american_odds=american,
                            implied_prob=yes_cents / 100.0,
                            raw=m,
                        )
                    ],
                    metadata={"ticker": m.get("ticker"), "layer": self.layer.value},
                )
            )
        return fragments

    @staticmethod
    def _parse_teams(title: str) -> tuple[str, str]:
        t = title
        for sep in (" vs ", " beat ", " to beat "):
            if sep in t.lower():
                parts = t.lower().split(sep)
                if len(parts) >= 2:
                    return parts[0].strip().title(), parts[-1].strip().title()
        return "TBD", title[:40]


def attach_kalshi_to_sportsbook_fragments(
    sportsbook: list[MarketFragment],
    kalshi: list[MarketFragment],
    *,
    threshold: int = 82,
) -> list[MarketFragment]:
    """Splice Kalshi yes/no legs onto matching sportsbook events."""
    merged = list(sportsbook)
    for k in kalshi:
        for sb in sportsbook:
            if match_event_titles(
                f"{sb.home_team} {sb.away_team}",
                sb.home_team,
                sb.away_team,
                threshold=threshold,
            ) and match_event_titles(
                f"{k.home_team} {k.away_team}",
                sb.home_team,
                sb.away_team,
                threshold=threshold,
            ):
                merged.append(
                    MarketFragment(
                        source="kalshi",
                        platform_kind=PlatformKind.PREDICTION_MARKET,
                        sport=sb.sport,
                        league=sb.league,
                        home_team=sb.home_team,
                        away_team=sb.away_team,
                        commence_time=sb.commence_time,
                        market_type=MarketType.YES_NO,
                        market_key=k.market_key,
                        quotes=k.quotes,
                        metadata={**k.metadata, "spliced_from": sb.source},
                    )
                )
                break
    return merged
