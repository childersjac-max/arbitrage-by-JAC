"""Allocation data types — extend existing opportunity dicts, do not replace them."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AllocatedLeg:
    source: str
    outcome: str
    price: float
    stake_weight: float
    stake_usd: float
    payout_usd: float
    balance_before: float
    balance_after: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "outcome": self.outcome,
            "price": self.price,
            "stake_weight": self.stake_weight,
            "stake_usd": self.stake_usd,
            "payout_usd": self.payout_usd,
            "balance_before": self.balance_before,
            "balance_after": self.balance_after,
        }


@dataclass
class SkippedOpportunity:
    opportunity_id: str
    event_name: str
    reason: str
    limiting_book: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.opportunity_id,
            "event_name": self.event_name,
            "reason": self.reason,
            "limiting_book": self.limiting_book,
        }


@dataclass
class AllocatedOpportunity:
    opportunity_id: str
    total_stake_usd: float
    expected_profit_usd: float
    roi_pct: float
    limiting_book: str | None
    capital_efficiency: float
    score: float
    feasible: bool
    legs: list[AllocatedLeg] = field(default_factory=list)
    rank: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "opportunity_id": self.opportunity_id,
            "total_stake_usd": round(self.total_stake_usd, 2),
            "expected_profit_usd": round(self.expected_profit_usd, 2),
            "roi_pct": self.roi_pct,
            "limiting_book": self.limiting_book,
            "capital_efficiency": round(self.capital_efficiency, 6),
            "score": round(self.score, 4),
            "feasible": self.feasible,
            "rank": self.rank,
            "legs": [leg.to_dict() for leg in self.legs],
        }


@dataclass
class PortfolioResult:
    selected: list[AllocatedOpportunity] = field(default_factory=list)
    skipped: list[SkippedOpportunity] = field(default_factory=list)
    total_deployed_usd: float = 0.0
    total_expected_profit_usd: float = 0.0
    balances_remaining: dict[str, float] = field(default_factory=dict)
    book_utilization: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "selected": [item.to_dict() for item in self.selected],
            "skipped": [item.to_dict() for item in self.skipped],
            "total_deployed_usd": round(self.total_deployed_usd, 2),
            "total_expected_profit_usd": round(self.total_expected_profit_usd, 2),
            "opportunities_selected": len(self.selected),
            "opportunities_skipped": len(self.skipped),
            "balances_remaining": {
                k: round(v, 2) for k, v in sorted(self.balances_remaining.items())
            },
            "book_utilization": {
                k: round(v, 4) for k, v in sorted(self.book_utilization.items())
            },
        }
