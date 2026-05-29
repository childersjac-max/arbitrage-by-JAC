"""American odds and implied-probability helpers."""

from __future__ import annotations


def american_to_decimal(american: float) -> float:
    if american >= 100:
        return (american / 100.0) + 1.0
    return (100.0 / abs(american)) + 1.0


def american_to_implied_prob(american: float) -> float:
    if american >= 100:
        return 100.0 / (american + 100.0)
    return abs(american) / (abs(american) + 100.0)


def prob_cents_to_american(cents: float) -> int:
    """Kalshi-style probability in cents (0–100) → American odds."""
    p = cents / 100.0
    if p <= 0 or p >= 1:
        return 100
    if p >= 0.5:
        return int(round(-(p / (1.0 - p)) * 100))
    return int(round(((1.0 - p) / p) * 100))


def predictit_price_to_american(price: float) -> int:
    """PredictIt dollar price (0–1) → American odds."""
    if price <= 0 or price >= 1:
        return 100
    return prob_cents_to_american(price * 100.0)


def two_way_arb_yield(price_a: float, price_b: float) -> tuple[float, float] | None:
    """
    Returns (yield_pct, implied_prob_gap) if arb exists, else None.
    yield_pct = (1 - sum(1/dec)) * 100
    """
    da = american_to_decimal(price_a)
    db = american_to_decimal(price_b)
    if da <= 1 or db <= 1:
        return None
    inv_sum = (1.0 / da) + (1.0 / db)
    if inv_sum >= 1.0:
        return None
    yield_pct = (1.0 - inv_sum) * 100.0
    gap = abs(american_to_implied_prob(price_a) - (1.0 - american_to_implied_prob(price_b)))
    return yield_pct, gap
