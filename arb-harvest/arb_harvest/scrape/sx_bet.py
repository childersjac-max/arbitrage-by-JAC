"""
SportX / SX Bet — public REST API (documented, no auth for market + order data).

  GET https://api.sx.bet/markets/active
  GET https://api.sx.bet/orders?marketHash={hash}
"""

from __future__ import annotations

from typing import Any

from arb_harvest.models import MarketQuote, NormalizedEvent, OutcomeQuote, SourceBook
from arb_harvest.net import PoliteHttpClient
from arb_harvest.normalize.sport_infer import infer_sport_key
from arb_harvest.scrape.base import SupplementalFetcher

SX_BASE = "https://api.sx.bet"

# Moneyline-style market types observed on active NFL markets
_ML_TYPES = frozenset({226, 52, 1})


def _percentage_odds_to_implied(raw: str | int) -> float | None:
    try:
        v = int(raw)
    except (TypeError, ValueError):
        return None
    # On-chain fixed-point: values ~1e19–1e20 encode implied probability (~0.24–0.76)
    if v > 10**18:
        p = v / 10**20
    else:
        p = v / 10**18
    if 0 < p < 1:
        return p
    return None


def _implied_to_american(p: float) -> int:
    if p <= 0 or p >= 1:
        return 100
    if p >= 0.5:
        return int(round(-(p / (1 - p)) * 100))
    return int(round(((1 - p) / p) * 100))


def _best_american_from_orders(orders: list[dict[str, Any]], outcome_one: bool) -> tuple[int | None, float | None]:
    best_p: float | None = None
    volume = 0.0
    for o in orders:
        if o.get("orderStatus") != "ACTIVE":
            continue
        if bool(o.get("isMakerBettingOutcomeOne")) != outcome_one:
            continue
        imp = _percentage_odds_to_implied(o.get("percentageOdds"))
        if imp is None:
            continue
        try:
            size = float(o.get("totalBetSize") or 0) / 1_000_000
        except (TypeError, ValueError):
            size = 0.0
        volume += size
        if best_p is None or imp < best_p:
            best_p = imp
    if best_p is None:
        return None, volume or None
    return _implied_to_american(best_p), volume or None


class SxBetFetcher(SupplementalFetcher):
    source_id = "sx_bet"

    def __init__(self, http: PoliteHttpClient):
        self.http = http

    def _active_markets(self) -> list[dict[str, Any]]:
        data = self.http.get_json(f"{SX_BASE}/markets/active")
        if not isinstance(data, dict):
            return []
        inner = data.get("data")
        if isinstance(inner, dict):
            return list(inner.get("markets") or [])
        return []

    def _orders(self, market_hash: str) -> list[dict[str, Any]]:
        data = self.http.get_json(f"{SX_BASE}/orders", params={"marketHash": market_hash})
        if not isinstance(data, dict):
            return []
        rows = data.get("data")
        return list(rows) if isinstance(rows, list) else []

    def fetch(self) -> list[NormalizedEvent]:
        events: list[NormalizedEvent] = []
        seen: set[str] = set()

        for m in self._active_markets():
            t1 = (m.get("teamOneName") or "").strip()
            t2 = (m.get("teamTwoName") or "").strip()
            if not t1 or not t2 or "field" in t2.lower():
                continue
            mtype = m.get("type")
            if mtype not in _ML_TYPES:
                continue
            if m.get("outcomeOneName") != t1 and " " in str(m.get("outcomeOneName") or ""):
                continue

            sport_key = infer_sport_key(
                f"{m.get('sportLabel', '')} {m.get('leagueLabel', '')} {t1} {t2}",
            )
            if sport_key == "unknown":
                continue

            eid = str(m.get("sportXeventId") or m.get("marketHash"))
            if eid in seen:
                continue
            seen.add(eid)

            mh = str(m.get("marketHash") or "")
            orders = self._orders(mh) if mh else []
            p1, vol1 = _best_american_from_orders(orders, True)
            p2, vol2 = _best_american_from_orders(orders, False)
            if p1 is None and p2 is None:
                continue

            outcomes: list[OutcomeQuote] = []
            if p1 is not None:
                outcomes.append(OutcomeQuote(name=t1, price_american=p1, volume=vol1))
            if p2 is not None:
                outcomes.append(OutcomeQuote(name=t2, price_american=p2, volume=vol2))

            book = SourceBook(
                source_id=self.source_id,
                title="SX Bet",
                markets=[MarketQuote(key="h2h", outcomes=outcomes)],
                raw=m,
            )
            events.append(
                NormalizedEvent(
                    event_id=eid,
                    sport_key=sport_key,
                    normalized_name="",
                    home_team=t1,
                    away_team=t2,
                    commence_time=str(m.get("gameTime") or ""),
                    books=[book],
                )
            )
        return events
