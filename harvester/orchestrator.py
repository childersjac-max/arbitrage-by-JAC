"""Async scheduler, merge logic, and unified JSON emission."""

from __future__ import annotations

import asyncio
import json
import random
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from time import perf_counter
from typing import Iterable

from harvester.adapters.base import (
    NotImplementedSourceAdapter,
    SourceAdapter,
    SourceAdapterError,
    SourceTransientError,
)
from harvester.adapters.betfair_stub import BetfairStubAdapter
from harvester.adapters.betmgm_stub import BetMgmStubAdapter
from harvester.adapters.draftkings_stub import DraftKingsStubAdapter
from harvester.adapters.fanduel_stub import FanDuelStubAdapter
from harvester.adapters.kalshi_public import KalshiPublicAdapter
from harvester.adapters.odds_api import TheOddsApiAdapter
from harvester.adapters.polymarket_public import PolymarketPublicAdapter
from harvester.config import HarvesterSettings, get_settings
from harvester.models import (
    AdapterFetchResult,
    ArbitrageBlock,
    BestPrice,
    MarketType,
    SourceQuote,
    SourceSnapshot,
    UnifiedEvent,
    utc_now,
)
from harvester.normalize.bridge import LocalLLMNormalizationBridge
from harvester.output.unified_stream import emit_file, emit_stdout


class HarvesterOrchestrator:
    """Coordinate source polling, entity normalization, merge, and output."""

    def __init__(
        self,
        settings: HarvesterSettings | None = None,
        adapters: list[SourceAdapter] | None = None,
        normalizer: LocalLLMNormalizationBridge | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.adapters = adapters or build_default_adapters(self.settings)
        self.normalizer = normalizer or LocalLLMNormalizationBridge(self.settings)

    async def run_once(self) -> list[UnifiedEvent]:
        """Fetch one tick from all adapters and return unified events."""

        results = await asyncio.gather(
            *[self._fetch_adapter(adapter) for adapter in self.adapters],
            return_exceptions=False,
        )
        quotes = [quote for result in results for quote in result.quotes]
        events = await merge_quotes(
            quotes,
            normalizer=self.normalizer,
            window_minutes=self.settings.harvester_merge_start_window_minutes,
        )
        if self.settings.harvester_output_path:
            emit_file(events, self.settings.harvester_output_path, pretty=self.settings.harvester_pretty_json)
        else:
            emit_stdout(events, pretty=self.settings.harvester_pretty_json)
        return events

    async def run_forever(self) -> None:
        """Poll forever at the configured interval."""

        while True:
            await self.run_once()
            await asyncio.sleep(self.settings.harvester_poll_interval_seconds)

    async def _fetch_adapter(self, adapter: SourceAdapter) -> AdapterFetchResult:
        """Fetch an adapter with timeout and retry on 429/5xx only."""

        attempts = max(1, self.settings.harvester_retry_attempts)
        for attempt in range(1, attempts + 1):
            started = perf_counter()
            try:
                result = await asyncio.wait_for(
                    adapter.fetch_quotes(),
                    timeout=self.settings.harvester_adapter_timeout_seconds,
                )
                _log_json(
                    "info",
                    "adapter_fetch",
                    adapter=adapter.source_id,
                    status=result.status,
                    quote_count=len(result.quotes),
                    latency_ms=round((perf_counter() - started) * 1000, 2),
                    message=result.message,
                )
                return result
            except SourceTransientError as exc:
                _log_json(
                    "warning",
                    "adapter_retry",
                    adapter=adapter.source_id,
                    attempt=attempt,
                    error_class=exc.__class__.__name__,
                    latency_ms=round((perf_counter() - started) * 1000, 2),
                )
                if attempt >= attempts:
                    return AdapterFetchResult(
                        source_id=adapter.source_id,
                        status="error",
                        message=str(exc),
                    )
                delay = self.settings.harvester_retry_base_seconds * (2 ** (attempt - 1))
                await asyncio.sleep(delay + random.uniform(0, delay / 2))
            except (SourceAdapterError, asyncio.TimeoutError, Exception) as exc:
                _log_json(
                    "error",
                    "adapter_error",
                    adapter=adapter.source_id,
                    error_class=exc.__class__.__name__,
                    latency_ms=round((perf_counter() - started) * 1000, 2),
                    message=str(exc),
                )
                return AdapterFetchResult(
                    source_id=adapter.source_id,
                    status="error",
                    message=str(exc),
                )
        return AdapterFetchResult(source_id=adapter.source_id, status="error")


async def merge_quotes(
    quotes: Iterable[SourceQuote],
    normalizer: LocalLLMNormalizationBridge,
    window_minutes: int = 30,
) -> list[UnifiedEvent]:
    """Merge source quotes into unified event-market payloads."""

    quote_list = list(quotes)
    names = [quote.raw_event_name for quote in quote_list]
    names.extend(quote.selection_name for quote in quote_list if quote.selection_name)
    normalized = await normalizer.normalize_batch(name for name in names if name)

    grouped: dict[tuple[str, datetime, str, str, str | None, float | None], list[SourceQuote]] = defaultdict(list)
    normalized_names: dict[str, str] = {}
    for quote in quote_list:
        normalized_event_name = normalized.get(quote.raw_event_name, quote.raw_event_name)
        window = floor_time_window(quote.start_time, window_minutes)
        normalized_event_id = make_normalized_event_id(quote.sport, window, normalized_event_name)
        normalized_names[normalized_event_id] = normalized_event_name
        selection = normalized.get(quote.selection_name or "", quote.selection_name) if quote.selection_name else None
        key = (
            quote.sport,
            window,
            normalized_event_id,
            market_type_value(quote.market_type),
            selection,
            quote.line,
        )
        grouped[key].append(quote)

    timestamp = utc_now()
    unified: list[UnifiedEvent] = []
    for (sport, window, normalized_event_id, market_type, selection, line), group in grouped.items():
        sources: dict[str, SourceSnapshot] = {}
        for quote in sorted(group, key=lambda item: item.fetched_at):
            sources[quote.source_id] = SourceSnapshot(
                raw_event_name=quote.raw_event_name,
                odds=quote.odds,
                volume=quote.volume,
                liquidity=quote.liquidity,
                url=quote.url,
                fetched_at=quote.fetched_at,
            )
        arbitrage = compute_arbitrage(sources, market_type)
        unified.append(
            UnifiedEvent(
                timestamp=timestamp,
                normalized_event_id=normalized_event_id,
                normalized_event_name=normalized_names[normalized_event_id],
                market_type=market_type,
                sport=sport,
                start_time=window,
                selection_name=selection,
                line=line,
                sources=sources,
                arbitrage=arbitrage,
            )
        )
    return sorted(
        unified,
        key=lambda event: (
            event.start_time,
            event.sport,
            event.normalized_event_id,
            str(event.market_type),
            event.selection_name or "",
            event.line if event.line is not None else 0.0,
        ),
    )


def compute_arbitrage(
    sources: dict[str, SourceSnapshot],
    market_type: str | MarketType,
) -> ArbitrageBlock | None:
    """Compute binary back/lay yield when comparable probability prices exist.

    The Odds API bookmaker prices are American odds and do not contain lay-side
    exchange prices, so this function intentionally omits an arbitrage block for
    those markets. Public prediction-market adapters may emit 0-1 binary prices.
    """

    if market_type_value(market_type) != MarketType.BINARY_YES_NO.value:
        return None
    priced = [
        (source_id, snapshot.odds)
        for source_id, snapshot in sources.items()
        if snapshot.odds is not None and 0.0 <= snapshot.odds <= 1.0
    ]
    if len(priced) < 2:
        return None
    best_back_source, best_back_price = max(priced, key=lambda item: item[1])
    best_lay_source, best_lay_price = min(priced, key=lambda item: item[1])
    if best_back_source == best_lay_source or best_back_price <= best_lay_price:
        return None
    return ArbitrageBlock(
        best_back=BestPrice(source=best_back_source, price=best_back_price),
        best_lay=BestPrice(source=best_lay_source, price=best_lay_price),
        yield_pct=round((best_back_price - best_lay_price) * 100.0, 6),
    )


def market_type_value(value: str | MarketType) -> str:
    """Return a stable string value for enum or raw market types."""

    return value.value if isinstance(value, MarketType) else str(value)


def floor_time_window(value: datetime, window_minutes: int) -> datetime:
    """Floor a timestamp to the configured merge window."""

    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    value = value.astimezone(timezone.utc)
    window = max(1, window_minutes)
    minute = (value.minute // window) * window
    return value.replace(minute=minute, second=0, microsecond=0)


def make_normalized_event_id(sport: str, window: datetime, normalized_event_name: str) -> str:
    """Create a stable normalized event identifier."""

    slug = re.sub(r"[^a-z0-9]+", "-", normalized_event_name.casefold()).strip("-")
    return f"{sport}:{window.isoformat()}:{slug}"


def build_default_adapters(settings: HarvesterSettings) -> list[SourceAdapter]:
    """Construct default adapters without adding any non-compliant sources."""

    adapters: list[SourceAdapter] = []
    if settings.the_odds_api_key:
        adapters.append(TheOddsApiAdapter(settings))
    else:
        adapters.append(
            NotImplementedSourceAdapter(
                "the_odds_api",
                "source_unavailable: THE_ODDS_API_KEY is not configured.",
            )
        )
    if settings.harvester_enable_polymarket:
        adapters.append(PolymarketPublicAdapter(settings))
    adapters.extend(
        [
            KalshiPublicAdapter(),
            BetfairStubAdapter(),
            DraftKingsStubAdapter(),
            FanDuelStubAdapter(),
            BetMgmStubAdapter(),
        ]
    )
    return adapters


def _log_json(level: str, event: str, **fields: object) -> None:
    """Write structured JSON logs to stderr."""

    payload = {
        "timestamp": utc_now().isoformat(),
        "level": level,
        "event": event,
        **{key: value for key, value in fields.items() if value is not None},
    }
    print(json.dumps(payload, separators=(",", ":"), default=str), file=sys.stderr)


async def run_once() -> list[UnifiedEvent]:
    """Convenience entrypoint for scripts."""

    return await HarvesterOrchestrator().run_once()


if __name__ == "__main__":
    asyncio.run(HarvesterOrchestrator().run_forever())
