"""Cross-book arbitrage detection on normalized events."""

from __future__ import annotations

from arb_harvest.models import ArbitrageSignal, NormalizedEvent, utc_now_iso


def _american_to_decimal(american: float) -> float:
    if american >= 100:
        return american / 100.0 + 1.0
    return 100.0 / abs(american) + 1.0


def _valid_american(price: float) -> bool:
    return price >= 100 or price <= -100


def _outcome_key(name: str, point: float | None) -> str:
    base = name.strip()
    if point is not None:
        sign = "+" if point > 0 else ""
        return f"{base} {sign}{point}".strip()
    return base


def detect_arbitrage(
    events: list[NormalizedEvent],
    min_yield_pct: float = 0.25,
) -> list[ArbitrageSignal]:
    signals: list[ArbitrageSignal] = []
    ts = utc_now_iso()

    for ev in events:
        # market_key -> outcome_key -> list of (source, price, volume)
        market_map: dict[str, dict[str, list[tuple[str, float, float | None]]]] = {}

        for book in ev.books:
            for mkt in book.markets:
                mkey = mkt.key
                if mkt.line is not None:
                    mkey = f"{mkey}_{mkt.line}"
                outcome_map = market_map.setdefault(mkey, {})
                for oc in mkt.outcomes:
                    price = float(oc.price_american)
                    if not _valid_american(price):
                        continue
                    okey = _outcome_key(oc.name, oc.point)
                    outcome_map.setdefault(okey, []).append(
                        (book.source_id, price, oc.volume)
                    )

        for market_type, outcome_map in market_map.items():
            if len(outcome_map) < 2:
                continue
            if len(outcome_map) > 3:
                continue

            best_per_outcome: list[tuple[str, str, float, float | None, float]] = []
            for outcome_name, quotes in outcome_map.items():
                best_src, best_price, best_vol = "", -1.0, None
                best_dec = 0.0
                for src, price, vol in quotes:
                    dec = _american_to_decimal(price)
                    if dec > best_dec:
                        best_dec = dec
                        best_src = src
                        best_price = price
                        best_vol = vol
                best_per_outcome.append(
                    (outcome_name, best_src, best_price, best_vol, best_dec)
                )

            sources = {x[1] for x in best_per_outcome}
            if len(sources) < 2:
                continue

            inv_sum = sum(1.0 / x[4] for x in best_per_outcome)
            if inv_sum >= 1.0:
                continue
            yield_pct = ((1.0 / inv_sum) - 1.0) * 100.0
            if yield_pct < min_yield_pct:
                continue

            legs = [
                {
                    "outcome": name,
                    "source": src,
                    "price_american": price,
                    "volume": vol,
                    "decimal_odds": dec,
                }
                for name, src, price, vol, dec in best_per_outcome
            ]
            a, b = best_per_outcome[0], best_per_outcome[1]
            signals.append(
                ArbitrageSignal(
                    timestamp=ts,
                    normalized_event_name=ev.normalized_name,
                    market_type=market_type,
                    source_a_odds_and_volume={
                        "source": a[1],
                        "outcome": a[0],
                        "price_american": a[2],
                        "volume": a[3],
                    },
                    source_b_odds_and_volume={
                        "source": b[1],
                        "outcome": b[0],
                        "price_american": b[2],
                        "volume": b[3],
                    },
                    calculated_arbitrage_yield_percentage=round(yield_pct, 4),
                    sport_key=ev.sport_key,
                    commence_time=ev.commence_time,
                    legs=legs,
                )
            )

    return sorted(
        signals,
        key=lambda s: s.calculated_arbitrage_yield_percentage,
        reverse=True,
    )
