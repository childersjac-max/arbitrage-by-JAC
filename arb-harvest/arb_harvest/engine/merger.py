"""Splice baseline events with supplemental fetcher payloads."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

from arb_harvest.models import NormalizedEvent
from arb_harvest.normalize import EventMatcher
from arb_harvest.scrape.base import SupplementalFetcher


def splice_events(
    baseline: list[NormalizedEvent],
    supplemental_batches: list[list[NormalizedEvent]],
    matcher: EventMatcher | None = None,
) -> list[NormalizedEvent]:
    matcher = matcher or EventMatcher()
    index = matcher.index(list(baseline))
    merged = list(index.values())

    for batch in supplemental_batches:
        for cand in batch:
            if cand.sport_key == "unknown":
                # Infer sport from best fuzzy match
                pass
            match = matcher.find_match(cand, index)
            if match:
                matcher.merge_books(match, cand)
            else:
                sig = matcher._signature(cand)
                cand.normalized_name = sig
                index[sig] = cand
                merged.append(cand)
    return merged


def fetch_supplemental_parallel(
    fetchers: list[SupplementalFetcher],
    max_workers: int = 8,
) -> list[list[NormalizedEvent]]:
    results: list[list[NormalizedEvent]] = []
    if not fetchers:
        return results
    with ThreadPoolExecutor(max_workers=min(max_workers, len(fetchers))) as pool:
        futures = {pool.submit(f.fetch): f for f in fetchers}
        for fut in as_completed(futures):
            try:
                results.append(fut.result())
            except Exception:
                results.append([])
    return results
