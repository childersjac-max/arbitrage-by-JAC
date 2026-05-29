"""Emit unified arbitrage board rows from a spliced board."""

from __future__ import annotations

from datetime import datetime, timezone

from harvest.models import MarketType, UnifiedArbitrageRow
from harvest.odds_math import american_to_decimal, is_valid_american, two_way_arb_yield_pct
from harvest.splice import SplicedBoard, board_display_names


def _quote_source_payload(q, frag) -> dict:
    dec = q.effective_decimal()
    return {
        "platform": q.platform,
        "odds": q.american_odds,
        "decimal_odds": round(dec, 4) if dec else None,
        "liquidity_volume": q.liquidity_volume,
        "outcome": q.outcome_label,
        "market_key": frag.market_key,
    }


def normalize_board(board: SplicedBoard) -> list[UnifiedArbitrageRow]:
    """Cross-book two-way arb: best price per outcome on distinct platforms."""
    display = board_display_names(board)
    rows: list[UnifiedArbitrageRow] = []
    now = datetime.now(timezone.utc).isoformat()

    for event_key, frags in board.by_event.items():
        event_name = display.get(event_key, event_key)
        by_market: dict[str, list] = {}
        for frag in frags:
            if frag.market_type not in (MarketType.MONEYLINE, MarketType.YES_NO, MarketType.SPREAD):
                continue
            by_market.setdefault(frag.market_key, []).append(frag)

        for market_key, market_frags in by_market.items():
            # outcome_label -> (frag, quote, decimal)
            best_per_outcome: dict[str, tuple] = {}
            for frag in market_frags:
                for q in frag.quotes:
                    dec = q.effective_decimal()
                    if dec is None and q.american_odds and is_valid_american(q.american_odds):
                        dec = american_to_decimal(q.american_odds)
                    if dec is None or dec <= 1:
                        continue
                    label = q.outcome_label.strip().lower()
                    prev = best_per_outcome.get(label)
                    if prev is None or dec > prev[2]:
                        best_per_outcome[label] = (frag, q, dec)

            if len(best_per_outcome) != 2:
                continue

            legs = list(best_per_outcome.values())
            (fa, qa, da), (fb, qb, db) = legs[0], legs[1]
            if fa.source == fb.source:
                continue

            yield_pct = two_way_arb_yield_pct(da, db)
            if yield_pct is None or yield_pct <= 0:
                continue

            mtype = market_frags[0].market_type.value
            rows.append(
                UnifiedArbitrageRow(
                    timestamp=now,
                    normalized_event_name=event_name,
                    market_type=mtype,
                    source_A=_quote_source_payload(qa, fa),
                    source_B=_quote_source_payload(qb, fb),
                    arbitrage_yield_percentage=yield_pct,
                )
            )

    rows.sort(key=lambda r: r.arbitrage_yield_percentage, reverse=True)
    return rows
