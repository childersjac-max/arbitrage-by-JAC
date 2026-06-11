"""Per-line arbitrage detection for h2h, spreads, totals, props, and alternates."""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from models import ArbitrageInfo, ArbitrageLeg, SourceQuote, UnifiedRecord

H2H_MARKETS = frozenset(
    {
        "h2h",
        "outrights",
        "draw_no_bet",
        "btts",
    }
)
SPREAD_MARKETS = frozenset(
    {
        "spreads",
        "alternate_spreads",
    }
)
TOTAL_MARKETS = frozenset(
    {
        "totals",
        "alternate_totals",
        "alternate_team_totals",
        "team_totals",
    }
)

OVER_ALIASES = frozenset({"over", "o", "yes"})
UNDER_ALIASES = frozenset({"under", "u", "no"})


def _normalize_band(outcome: str) -> str | None:
    text = outcome.strip().lower()
    if text in OVER_ALIASES or text.startswith("over"):
        return "over"
    if text in UNDER_ALIASES or text.startswith("under"):
        return "under"
    if text in {"yes", "no"}:
        return text
    return None


def line_bucket_key(market_type: str, quote: SourceQuote) -> str | None:
    """Group quotes that share the same line for arb comparison."""
    mt = (market_type or "").strip().lower()
    if mt in H2H_MARKETS:
        return "__line__"
    if mt in SPREAD_MARKETS:
        if quote.line is None:
            return None
        return f"spread:{abs(float(quote.line)):.6g}"
    if mt in TOTAL_MARKETS:
        if quote.line is None:
            return None
        return f"total:{float(quote.line):.6g}"
    if quote.line is not None:
        return f"prop:{float(quote.line):.6g}"
    return "__prop__"


def side_key(market_type: str, quote: SourceQuote) -> str:
    """Unique side within a line bucket (never cross mismatched lines)."""
    mt = (market_type or "").strip().lower()
    band = _normalize_band(quote.outcome)
    if mt in TOTAL_MARKETS and band:
        return band
    if mt not in H2H_MARKETS and mt not in SPREAD_MARKETS and band:
        return band
    if mt in SPREAD_MARKETS and quote.line is not None:
        return f"{quote.outcome}|{float(quote.line):.6g}"
    return quote.outcome


def _best_price_per_side(
    sources: dict[str, list[SourceQuote]],
    market_type: str,
    line_bucket: str,
) -> dict[str, tuple[float, str, SourceQuote]]:
    best: dict[str, tuple[float, str, SourceQuote]] = {}
    for book_key, quotes in sources.items():
        for quote in quotes:
            if quote.price <= 1.0:
                continue
            if line_bucket_key(market_type, quote) != line_bucket:
                continue
            sk = side_key(market_type, quote)
            current = best.get(sk)
            if current is None or quote.price > current[0]:
                best[sk] = (quote.price, book_key, quote)
    return best


def detect_two_way_arb(
    best_by_side: dict[str, tuple[float, str, SourceQuote]],
) -> ArbitrageInfo | None:
    """Arb when sum(1/best_price) < 1 across all sides on the same line."""
    if len(best_by_side) < 2:
        return None

    implied_sum = sum(1.0 / price for price, _, _ in best_by_side.values())
    if implied_sum >= 1.0:
        return None

    yield_pct = (1.0 / implied_sum - 1.0) * 100.0
    legs: list[ArbitrageLeg] = []
    for _, (price, book, quote) in best_by_side.items():
        weight = (1.0 / price) / implied_sum
        legs.append(
            ArbitrageLeg(
                source=book,
                outcome=quote.outcome,
                price=price,
                stake_weight=round(weight, 6),
            )
        )
    return ArbitrageInfo(
        yield_pct=round(yield_pct, 4),
        implied_sum=round(implied_sum, 6),
        legs=legs,
    )


def detect_best_arb_for_record(record: UnifiedRecord) -> ArbitrageInfo | None:
    """Return the highest-yield arb across all line buckets in this record."""
    buckets: set[str] = set()
    for quotes in record.sources.values():
        for quote in quotes:
            bucket = line_bucket_key(record.market_type, quote)
            if bucket is not None:
                buckets.add(bucket)

    if not buckets:
        buckets = {"__line__"}

    best: ArbitrageInfo | None = None
    for bucket in buckets:
        sides = _best_price_per_side(record.sources, record.market_type, bucket)
        arb = detect_two_way_arb(sides)
        if arb is not None and (best is None or arb.yield_pct > best.yield_pct):
            best = arb
    return best


def split_record_by_line(record: UnifiedRecord) -> list[UnifiedRecord]:
    """Split one event/market record into one record per line bucket."""
    bucket_sources: dict[str, dict[str, list[SourceQuote]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for book_key, quotes in record.sources.items():
        for quote in quotes:
            bucket = line_bucket_key(record.market_type, quote)
            if bucket is None:
                continue
            bucket_sources[bucket][book_key].append(quote)

    if not bucket_sources:
        return [record]

    api_event_id = str(record.metadata.get("api_event_id") or record.event_id)
    results: list[UnifiedRecord] = []
    for bucket, sources in bucket_sources.items():
        line_val: float | None = None
        if ":" in bucket:
            try:
                line_val = float(bucket.split(":", 1)[1])
            except ValueError:
                line_val = None

        meta = dict(record.metadata)
        meta["line_bucket"] = bucket
        meta["api_event_id"] = api_event_id
        if line_val is not None:
            meta["line"] = line_val

        results.append(
            UnifiedRecord(
                timestamp=record.timestamp,
                event_id=f"{api_event_id}:{record.market_type}:{bucket}",
                sport_key=record.sport_key,
                normalized_event_name=record.normalized_event_name,
                market_type=record.market_type,
                commence_time=record.commence_time,
                sources={book: list(qs) for book, qs in sources.items()},
                arbitrage=None,
                metadata=meta,
            )
        )
    return results


def expand_records_to_lines(records: Iterable[UnifiedRecord]) -> list[UnifiedRecord]:
    expanded: list[UnifiedRecord] = []
    for record in records:
        expanded.extend(split_record_by_line(record))
    return expanded


def combinations_for_line_record(record: UnifiedRecord) -> int:
    """Book combinations evaluated on this line (product of books per side)."""
    bucket = str(record.metadata.get("line_bucket") or "__line__")
    sides: dict[str, set[str]] = defaultdict(set)
    for book_key, quotes in record.sources.items():
        for quote in quotes:
            if quote.price <= 1.0:
                continue
            quote_bucket = line_bucket_key(record.market_type, quote)
            if quote_bucket != bucket and bucket != "__line__":
                continue
            sides[side_key(record.market_type, quote)].add(book_key)

    if len(sides) < 2:
        return 0

    total = 1
    for books in sides.values():
        total *= len(books)
    return total


def detect_h2h_arbitrage(record: UnifiedRecord) -> ArbitrageInfo | None:
    """Backward-compatible alias — delegates to per-line engine."""
    return detect_best_arb_for_record(record)
