"""
Polymarket — public Gamma + CLOB APIs for Yes/No prices and book depth.

Gamma markets: https://gamma-api.polymarket.com/markets
CLOB order book: https://clob.polymarket.com/book?token_id=...
"""

from __future__ import annotations

import json
import re
from typing import Any

from arb_harvest.models import MarketQuote, NormalizedEvent, OutcomeQuote, SourceBook
from arb_harvest.net import PoliteHttpClient
from arb_harvest.scrape.base import SupplementalFetcher

GAMMA_BASE = "https://gamma-api.polymarket.com"
CLOB_BASE = "https://clob.polymarket.com"


def _prob_to_american(p: float) -> int:
    if p <= 0 or p >= 1:
        return 100
    if p >= 0.5:
        return int(round(-(p / (1 - p)) * 100))
    return int(round(((1 - p) / p) * 100))


class PolymarketFetcher(SupplementalFetcher):
    source_id = "polymarket"

    def __init__(self, http: PoliteHttpClient):
        self.http = http

    def _active_markets(self, limit: int = 150) -> list[dict[str, Any]]:
        data = self.http.get_json(
            f"{GAMMA_BASE}/markets",
            params={"active": "true", "closed": "false", "limit": limit},
        )
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return list(data.get("data") or data.get("markets") or [])
        return []

    def _book_depth(self, token_id: str) -> float | None:
        data = self.http.get_json(f"{CLOB_BASE}/book", params={"token_id": token_id})
        if not isinstance(data, dict):
            return None
        bids = data.get("bids") or []
        total = 0.0
        for row in bids[:8]:
            if isinstance(row, dict):
                total += float(row.get("size") or 0)
            elif isinstance(row, (list, tuple)) and len(row) >= 2:
                total += float(row[1])
        return total if total > 0 else None

    def _parse_outcome_prices(self, market: dict[str, Any]) -> tuple[float | None, float | None]:
        """Return (yes_prob, no_prob) in 0–1 if available."""
        op = market.get("outcomePrices")
        if isinstance(op, str):
            try:
                op = json.loads(op)
            except json.JSONDecodeError:
                op = None
        if isinstance(op, list) and len(op) >= 2:
            try:
                yes = float(op[0])
                no = float(op[1])
                return yes, no
            except (TypeError, ValueError):
                pass
        # Fallback: bestBid / bestAsk on outcome tokens
        yes_ask = market.get("bestAsk")
        if yes_ask is not None:
            try:
                return float(yes_ask), 1.0 - float(yes_ask)
            except (TypeError, ValueError):
                pass
        return None, None

    def fetch(self) -> list[NormalizedEvent]:
        events: list[NormalizedEvent] = []
        for m in self._active_markets():
            question = (m.get("question") or m.get("title") or "").strip()
            if not question:
                continue
            q_lower = question.lower()
            if " vs " not in q_lower and " beat " not in q_lower:
                continue
            yes_p, no_p = self._parse_outcome_prices(m)
            if yes_p is None:
                continue
            clob_ids = m.get("clobTokenIds")
            if isinstance(clob_ids, str):
                try:
                    clob_ids = json.loads(clob_ids)
                except json.JSONDecodeError:
                    clob_ids = []
            token_id = clob_ids[0] if isinstance(clob_ids, list) and clob_ids else None
            volume = self._book_depth(str(token_id)) if token_id else None
            outcomes = [
                OutcomeQuote(
                    name="Yes",
                    price_american=_prob_to_american(yes_p),
                    implied_prob=yes_p,
                    volume=volume,
                ),
            ]
            if no_p is not None:
                outcomes.append(
                    OutcomeQuote(
                        name="No",
                        price_american=_prob_to_american(no_p),
                        implied_prob=no_p,
                    )
                )
            parts = _split_vs(question)
            home_raw, away_raw = (parts if parts else (question, ""))
            book = SourceBook(
                source_id=self.source_id,
                title="Polymarket",
                markets=[MarketQuote(key="binary_yes_no", outcomes=outcomes)],
                raw=m,
            )
            events.append(
                NormalizedEvent(
                    event_id=str(m.get("id") or m.get("conditionId") or question),
                    sport_key="unknown",
                    normalized_name="",
                    home_team=home_raw,
                    away_team=away_raw or "",
                    commence_time=m.get("endDate") or m.get("endDateIso") or "",
                    books=[book],
                )
            )
        return events


def _split_vs(text: str) -> tuple[str, str] | None:
    for sep in (r"\s+vs\.?\s+", r"\s+beat\s+"):
        parts = re.split(sep, text, maxsplit=1, flags=re.I)
        if len(parts) == 2:
            return parts[0].strip(), parts[1].strip()
    return None
