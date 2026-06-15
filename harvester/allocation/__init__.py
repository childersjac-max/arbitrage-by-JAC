"""Portfolio-level capital allocation across arbitrage opportunities."""

from allocation.balances import get_book_balances, save_book_balances
from allocation.optimizer import (
    allocate_stakes_for_opportunity,
    compute_max_size,
    enrich_opportunities,
    optimize_portfolio,
    profit_at_size,
    score_arb,
)

__all__ = [
    "allocate_stakes_for_opportunity",
    "compute_max_size",
    "enrich_opportunities",
    "get_book_balances",
    "optimize_portfolio",
    "profit_at_size",
    "save_book_balances",
    "score_arb",
]
