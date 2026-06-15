"""
Portfolio optimizer for arbitrage opportunities under per-book balance constraints.

Strategy (greedy re-ranking with dynamic balances):
1. Score each opportunity at its max executable size given current balances.
2. Select highest-score feasible arb, allocate stakes, deduct balances.
3. Re-rank remaining opportunities on updated balances until none fit.

This is a resource-allocation / multi-constraint knapsack variant where each arb
consumes coordinated capital across multiple books.
"""

from __future__ import annotations

import math
from copy import deepcopy
from typing import Any

from allocation.models import (
    AllocatedLeg,
    AllocatedOpportunity,
    PotentialPlay,
    PortfolioResult,
    SkippedOpportunity,
)
from settings import HarvesterSettings, get_settings
from target_sources import TARGET_SOURCE_BY_KEY


def _normalized_weights(legs: list[dict[str, Any]]) -> list[float]:
    raw = [max(float(leg.get("stake_weight") or 0.0), 0.0) for leg in legs]
    total = sum(raw)
    if total <= 0:
        n = len(legs)
        return [1.0 / n] * n if n else []
    return [w / total for w in raw]


def profit_at_size(total_stake_usd: float, yield_pct: float) -> float:
    """Equal-profit arb: profit scales linearly with total stake."""
    return total_stake_usd * (float(yield_pct) / 100.0)


def compute_max_size(
    opportunity: dict[str, Any],
    balances: dict[str, float],
    *,
    min_leg_stake_usd: float = 1.0,
) -> tuple[float, str | None]:
    """
    Maximum total stake before any leg exceeds its book balance.

    For leg i with normalized weight w_i on book b_i:
        stake_i = total_stake * w_i  <=  balances[b_i]
        => total_stake <= balances[b_i] / w_i  for all i
    """
    legs = opportunity.get("legs") or []
    if len(legs) < 2:
        return 0.0, None

    weights = _normalized_weights(legs)
    max_total = math.inf
    limiting_book: str | None = None

    for leg, weight in zip(legs, weights):
        if weight <= 0:
            return 0.0, None
        book = str(leg.get("source") or "")
        available = float(balances.get(book, 0.0))
        cap = available / weight
        if cap < max_total:
            max_total = cap
            limiting_book = book

    if not math.isfinite(max_total) or max_total <= 0:
        return 0.0, limiting_book

    # Enforce minimum stake per leg (sportsbook minimum bet).
    min_total_for_legs = 0.0
    for weight in weights:
        if weight > 0:
            min_total_for_legs = max(min_total_for_legs, min_leg_stake_usd / weight)

    if max_total < min_total_for_legs:
        return 0.0, limiting_book

    return round(max_total, 2), limiting_book


def compute_max_size_if_rebalanced(
    opportunity: dict[str, Any],
    total_capital_usd: float,
    *,
    min_leg_stake_usd: float = 1.0,
) -> float:
    """
    Max stake if the user can freely move all funds across books for this arb.

    With reallocation, total stake is capped by aggregate capital (not per-book
  distribution). Profit still scales linearly, so deploying all capital on one
  arb maximizes $ profit for that play.
    """
    legs = opportunity.get("legs") or []
    if len(legs) < 2 or total_capital_usd <= 0:
        return 0.0

    weights = _normalized_weights(legs)
    min_total = 0.0
    for weight in weights:
        if weight > 0:
            min_total = max(min_total, min_leg_stake_usd / weight)

    if total_capital_usd < min_total:
        return 0.0

    return round(total_capital_usd, 2)


def build_fund_relocation_plan(
    current_balances: dict[str, float],
    allocated_legs: list[AllocatedLeg],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Per-book targets vs current balances when funding the ideal arb.

    Returns (fund_targets, funding_sources) where:
    - fund_targets: books that need stakes; delta_usd > 0 means deposit/transfer in
    - funding_sources: books with spare cash after funding the play
    """
    required: dict[str, float] = {}
    for leg in allocated_legs:
        required[leg.source] = required.get(leg.source, 0.0) + leg.stake_usd

    fund_targets: list[dict[str, Any]] = []
    for leg in allocated_legs:
        book = leg.source
        if any(t["book"] == book for t in fund_targets):
            continue
        current = float(current_balances.get(book, 0.0))
        need = round(required.get(book, 0.0), 2)
        src = TARGET_SOURCE_BY_KEY.get(book)
        fund_targets.append(
            {
                "book": book,
                "book_name": src.name if src else book,
                "current_usd": round(current, 2),
                "required_usd": need,
                "delta_usd": round(need - current, 2),
            }
        )

    funding_sources: list[dict[str, Any]] = []
    for book, balance in current_balances.items():
        spare = round(balance - required.get(book, 0.0), 2)
        if spare > 0:
            src = TARGET_SOURCE_BY_KEY.get(book)
            funding_sources.append(
                {
                    "book": book,
                    "book_name": src.name if src else book,
                    "available_usd": spare,
                }
            )

    fund_targets.sort(key=lambda row: -row["delta_usd"])
    funding_sources.sort(key=lambda row: -row["available_usd"])
    return fund_targets, funding_sources


def find_best_potential_play(
    opportunities: list[dict[str, Any]],
    balances: dict[str, float],
    *,
    settings: HarvesterSettings | None = None,
) -> PotentialPlay | None:
    """
    Highest $ profit single arb if all available funds are moved to the right books.

    Picks the opportunity with the largest profit_at_size(total_capital, roi).
    """
    settings = settings or get_settings()
    total_capital = sum(balances.values())
    if total_capital <= 0 or not opportunities:
        return None

    best_opp: dict[str, Any] | None = None
    best_size = 0.0
    best_profit = -1.0

    for opp in opportunities:
        yield_pct = float(opp.get("yield_pct") or 0.0)
        if yield_pct < settings.min_allocation_roi_pct:
            continue

        size = compute_max_size_if_rebalanced(
            opp,
            total_capital,
            min_leg_stake_usd=settings.min_leg_stake_usd,
        )
        if size <= 0:
            continue

        profit = profit_at_size(size, yield_pct)
        if profit < settings.min_allocation_profit_usd:
            continue

        if profit > best_profit:
            best_profit = profit
            best_opp = opp
            best_size = size

    if best_opp is None:
        return None

    current_size, _ = compute_max_size(
        best_opp,
        balances,
        min_leg_stake_usd=settings.min_leg_stake_usd,
    )
    current_profit = profit_at_size(current_size, float(best_opp.get("yield_pct") or 0.0))

    ideal_legs = allocate_stakes_for_opportunity(best_opp, best_size, balances)
    fund_targets, funding_sources = build_fund_relocation_plan(balances, ideal_legs)

    return PotentialPlay(
        opportunity_id=str(best_opp.get("id") or ""),
        event_name=str(best_opp.get("event_name") or ""),
        sport_key=str(best_opp.get("sport_key") or ""),
        market_type=str(best_opp.get("market_type") or ""),
        roi_pct=float(best_opp.get("yield_pct") or 0.0),
        total_capital_usd=total_capital,
        max_stake_usd=best_size,
        potential_profit_usd=best_profit,
        current_profit_usd=current_profit,
        profit_uplift_usd=round(best_profit - current_profit, 2),
        fund_targets=fund_targets,
        funding_sources=funding_sources,
        legs=[leg.to_dict() for leg in ideal_legs],
    )


def score_arb(
    opportunity: dict[str, Any],
    max_size_usd: float,
    *,
    settings: HarvesterSettings | None = None,
    total_balance_usd: float | None = None,
) -> float:
    """
    Ranking formula balancing absolute profit, ROI, and capital concentration.

    score = (profit * W_profit) + (ROI * W_roi) - (deploy_ratio * W_penalty)

    Returns -1 when below minimum thresholds (candidate skipped).
    """
    settings = settings or get_settings()
    yield_pct = float(opportunity.get("yield_pct") or 0.0)
    profit = profit_at_size(max_size_usd, yield_pct)

    if profit < settings.min_allocation_profit_usd:
        return -1.0
    if yield_pct < settings.min_allocation_roi_pct:
        return -1.0

    deploy_ratio = 0.0
    if total_balance_usd and total_balance_usd > 0:
        deploy_ratio = max_size_usd / total_balance_usd

    return (
        settings.alloc_weight_profit * profit
        + settings.alloc_weight_roi * yield_pct
        - settings.alloc_weight_capital_penalty * deploy_ratio * 100.0
    )


def allocate_stakes_for_opportunity(
    opportunity: dict[str, Any],
    total_stake_usd: float,
    balances: dict[str, float],
) -> list[AllocatedLeg]:
    """Split total stake across legs using stake_weight proportions."""
    legs = opportunity.get("legs") or []
    weights = _normalized_weights(legs)
    allocated: list[AllocatedLeg] = []

    for leg, weight in zip(legs, weights):
        book = str(leg.get("source") or "")
        stake = round(total_stake_usd * weight, 2)
        price = float(leg.get("price") or 0.0)
        before = float(balances.get(book, 0.0))
        after = round(before - stake, 2)
        allocated.append(
            AllocatedLeg(
                source=book,
                outcome=str(leg.get("outcome") or ""),
                price=price,
                stake_weight=float(leg.get("stake_weight") or 0.0),
                stake_usd=stake,
                payout_usd=round(stake * price, 2),
                balance_before=before,
                balance_after=after,
            )
        )
    return allocated


def _apply_allocation_to_balances(
    balances: dict[str, float],
    allocated_legs: list[AllocatedLeg],
) -> None:
    for leg in allocated_legs:
        balances[leg.source] = round(balances.get(leg.source, 0.0) - leg.stake_usd, 2)


def _book_utilization(
    initial: dict[str, float],
    remaining: dict[str, float],
) -> dict[str, float]:
    util: dict[str, float] = {}
    for book, start in initial.items():
        if start <= 0:
            util[book] = 0.0
            continue
        used = max(start - remaining.get(book, 0.0), 0.0)
        util[book] = round(used / start, 4)
    return util


def optimize_portfolio(
    opportunities: list[dict[str, Any]],
    balances: dict[str, float],
    *,
    settings: HarvesterSettings | None = None,
) -> PortfolioResult:
    """
    Greedy portfolio selection with dynamic balance updates.

  Procedure:
    1. Copy starting balances.
    2. Loop until no feasible arb remains:
       a. Recompute max_size + score for every remaining opportunity.
       b. Pick highest score.
       c. Allocate stakes, deduct balances, record selection.
    3. Return portfolio summary + skipped list.
    """
    settings = settings or get_settings()
    working = deepcopy(balances)
    initial = deepcopy(balances)
    total_balance = sum(initial.values())

    remaining_opps = list(opportunities)
    selected: list[AllocatedOpportunity] = []
    skipped: list[SkippedOpportunity] = []
    rank = 0

    while remaining_opps:
        best_idx = -1
        best_score = -1.0
        best_size = 0.0
        best_limit: str | None = None

        for idx, opp in enumerate(remaining_opps):
            max_size, limit_book = compute_max_size(
                opp,
                working,
                min_leg_stake_usd=settings.min_leg_stake_usd,
            )
            if max_size <= 0:
                continue
            sc = score_arb(
                opp,
                max_size,
                settings=settings,
                total_balance_usd=total_balance,
            )
            if sc > best_score:
                best_score = sc
                best_idx = idx
                best_size = max_size
                best_limit = limit_book

        if best_idx < 0:
            break

        opp = remaining_opps.pop(best_idx)
        rank += 1
        legs = allocate_stakes_for_opportunity(opp, best_size, working)
        _apply_allocation_to_balances(working, legs)

        profit = profit_at_size(best_size, float(opp.get("yield_pct") or 0.0))
        selected.append(
            AllocatedOpportunity(
                opportunity_id=str(opp.get("id") or ""),
                total_stake_usd=best_size,
                expected_profit_usd=profit,
                roi_pct=float(opp.get("yield_pct") or 0.0),
                limiting_book=best_limit,
                capital_efficiency=profit / best_size if best_size else 0.0,
                score=best_score,
                feasible=True,
                legs=legs,
                rank=rank,
            )
        )

    # Mark everything not selected as skipped with reason.
    selected_ids = {item.opportunity_id for item in selected}
    skip_by_id: dict[str, SkippedOpportunity] = {}
    for opp in opportunities:
        oid = str(opp.get("id") or "")
        if oid in selected_ids:
            continue
        max_size, limit_book = compute_max_size(
            opp,
            balances,
            min_leg_stake_usd=settings.min_leg_stake_usd,
        )
        if max_size <= 0:
            reason = f"insufficient_balance:{limit_book or 'unknown'}"
        else:
            profit = profit_at_size(max_size, float(opp.get("yield_pct") or 0.0))
            if profit < settings.min_allocation_profit_usd:
                reason = "below_min_profit"
            elif float(opp.get("yield_pct") or 0.0) < settings.min_allocation_roi_pct:
                reason = "below_min_roi"
            else:
                reason = "outranked_by_higher_score"
        skip = SkippedOpportunity(
            opportunity_id=oid,
            event_name=str(opp.get("event_name") or ""),
            reason=reason,
            limiting_book=limit_book,
        )
        skipped.append(skip)
        skip_by_id[oid] = skip

    total_deployed = sum(item.total_stake_usd for item in selected)
    total_profit = sum(item.expected_profit_usd for item in selected)

    return PortfolioResult(
        selected=selected,
        skipped=skipped,
        total_deployed_usd=total_deployed,
        total_expected_profit_usd=total_profit,
        balances_remaining=working,
        book_utilization=_book_utilization(initial, working),
    )


def enrich_opportunities(
    opportunities: list[dict[str, Any]],
    portfolio: PortfolioResult,
) -> list[dict[str, Any]]:
    """Merge allocation fields into existing opportunity dicts for the dashboard."""
    by_id = {item.opportunity_id: item for item in portfolio.selected}
    skip_by_id = {item.opportunity_id: item for item in portfolio.skipped}
    enriched: list[dict[str, Any]] = []

    for opp in opportunities:
        row = dict(opp)
        oid = str(opp.get("id") or "")
        alloc = by_id.get(oid)
        if alloc is None:
            skip = skip_by_id.get(oid)
            row["allocation"] = {
                "feasible": False,
                "selected": False,
                "total_stake_usd": 0.0,
                "expected_profit_usd": 0.0,
                "limiting_book": skip.limiting_book if skip else None,
                "skip_reason": skip.reason if skip else None,
            }
            enriched.append(row)
            continue

        leg_stakes = {leg.source: leg for leg in alloc.legs}
        legs_out = []
        for leg in row.get("legs") or []:
            leg_row = dict(leg)
            stake = leg_stakes.get(str(leg.get("source") or ""))
            if stake:
                leg_row.update(stake.to_dict())
            legs_out.append(leg_row)

        row["legs"] = legs_out
        row["allocation"] = {
            "feasible": True,
            "selected": True,
            "rank": alloc.rank,
            "total_stake_usd": alloc.total_stake_usd,
            "expected_profit_usd": alloc.expected_profit_usd,
            "limiting_book": alloc.limiting_book,
            "capital_efficiency": alloc.capital_efficiency,
            "score": alloc.score,
        }
        enriched.append(row)

    return enriched


def mark_best_potential_play(
    opportunities: list[dict[str, Any]],
    potential: PotentialPlay | None,
) -> list[dict[str, Any]]:
    """Flag the highest potential $ play in the opportunity list."""
    if not potential:
        return opportunities
    pid = potential.opportunity_id
    for row in opportunities:
        is_best = str(row.get("id") or "") == pid
        row["is_best_potential"] = is_best
        if is_best:
            alloc = row.setdefault("allocation", {})
            alloc["potential_profit_usd"] = potential.potential_profit_usd
            alloc["profit_uplift_usd"] = potential.profit_uplift_usd
    return opportunities
