"""Odds conversion and arbitrage yield helpers."""

from __future__ import annotations


def american_to_decimal(american: int) -> float:
    if american >= 100:
        return american / 100.0 + 1.0
    if american <= -100:
        return 100.0 / abs(american) + 1.0
    raise ValueError(f"Invalid American odds: {american}")


def prob_cents_to_american(cents: float) -> int:
    p = cents / 100.0
    if p <= 0 or p >= 1:
        return 100
    if p >= 0.5:
        return round(-(p / (1 - p)) * 100)
    return round(((1 - p) / p) * 100)


def is_valid_american(price: int) -> bool:
    return price >= 100 or price <= -100


def two_way_arb_yield_pct(decimal_a: float, decimal_b: float) -> float | None:
    """Binary market: best prices on opposite sides → yield % if < 100% implied."""
    imp = (1.0 / decimal_a) + (1.0 / decimal_b)
    if imp >= 1.0:
        return None
    return round(((1.0 / imp) - 1.0) * 100.0, 4)
