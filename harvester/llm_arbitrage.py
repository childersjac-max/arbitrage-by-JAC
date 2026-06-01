"""Local LLM (Ollama) analysis of cross-source arbitrage opportunities."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from config import get_settings
from models import ArbitrageInfo, ArbitrageLeg, UnifiedRecord
from normalization.bridge import ensure_local_llm_importable
from target_sources import (
    CATEGORY_LABELS,
    TARGET_SOURCE_BY_KEY,
    TARGET_SOURCES,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a sports arbitrage analyst. You receive REAL odds JSON from a lawful aggregator.
Your job: find cross-source arbitrage opportunities ONLY among the listed target platforms.

RULES:
- Use ONLY sources present in the input data. Never invent prices or books.
- Decimal odds only. Arb exists when sum(1/best_decimal_price_per_outcome) < 1 across different sources.
- Consider sportsbooks, prediction markets, and exchanges as comparable ONLY when outcomes clearly match.
- If data is missing for a platform, do not claim an arb using that platform.
- Output ONLY valid JSON (no markdown).

OUTPUT SCHEMA:
{
  "opportunities": [
    {
      "event_id": "string",
      "yield_pct": 0.0,
      "implied_sum": 0.0,
      "legs": [
        {"source_key": "draftkings", "outcome": "Team A", "price": 2.1, "stake_weight": 0.48}
      ],
      "reasoning": "one sentence",
      "sources_used": ["draftkings", "fanduel"]
    }
  ]
}

If no arbs: {"opportunities": []}
"""


def _target_source_catalog() -> str:
    lines: list[str] = []
    current_cat = ""
    for src in TARGET_SOURCES:
        cat = CATEGORY_LABELS.get(src.category, src.category)
        if cat != current_cat:
            current_cat = cat
            lines.append(f"\n{cat}:")
        status = "direct adapter required" if src.direct_only else "via Odds API aliases"
        lines.append(f"  - {src.key} ({src.name}) [{status}]")
    return "\n".join(lines)


def _compact_events_payload(records: list[UnifiedRecord], *, limit: int) -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    for record in records[:limit]:
        sources: dict[str, list[dict[str, Any]]] = {}
        for book_key, quotes in record.sources.items():
            sources[book_key] = [
                {"outcome": q.outcome, "price": q.price, "line": q.line}
                for q in quotes
            ]
        payload.append(
            {
                "event_id": record.event_id,
                "event_name": record.normalized_event_name,
                "sport_key": record.sport_key,
                "market_type": record.market_type,
                "commence_time": record.commence_time.isoformat() if record.commence_time else None,
                "sources": sources,
            }
        )
    return payload


def _extract_json(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("No JSON object in LLM output")
    return json.loads(stripped[start : end + 1])


def _arb_from_llm_item(item: dict[str, Any]) -> ArbitrageInfo | None:
    try:
        yield_pct = float(item.get("yield_pct") or 0)
        implied_sum = float(item.get("implied_sum") or 0)
        legs_raw = item.get("legs") or []
        legs: list[ArbitrageLeg] = []
        for leg in legs_raw:
            if not isinstance(leg, dict):
                continue
            legs.append(
                ArbitrageLeg(
                    source=str(leg.get("source_key") or leg.get("source") or ""),
                    outcome=str(leg.get("outcome") or ""),
                    price=float(leg.get("price") or 0),
                    stake_weight=float(leg.get("stake_weight") or 0),
                )
            )
        if yield_pct <= 0 or len(legs) < 2:
            return None
        return ArbitrageInfo(yield_pct=round(yield_pct, 4), implied_sum=round(implied_sum, 6), legs=legs)
    except (TypeError, ValueError):
        return None


async def analyze_arbitrage_with_llm(records: list[UnifiedRecord]) -> dict[str, dict[str, Any]]:
    """
    Ask local Ollama to evaluate arbs across target sources.

    Returns event_id -> {arbitrage, reasoning, sources_used, method}.
    """
    settings = get_settings()
    if not settings.use_llm_arbitrage:
        return {}

    limit = settings.llm_arb_max_events
    events = _compact_events_payload(records, limit=limit)
    if not events:
        return {}

    user_msg = (
        "TARGET PLATFORMS (only consider these):\n"
        f"{_target_source_catalog()}\n\n"
        f"EVENTS WITH ODDS ({len(events)} shown, decimal):\n"
        f"{json.dumps(events, ensure_ascii=False)}\n\n"
        "Find arbitrage opportunities across the target sources. "
        f"Minimum yield to report: {settings.min_arb_yield_pct}%."
    )

    ensure_local_llm_importable()
    from ollama_connect import get_effective_ollama_model, ollama_chat_completion, resolve_ollama

    await resolve_ollama()
    model = await get_effective_ollama_model()
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_msg},
    ]

    try:
        raw = await ollama_chat_completion(
            messages,
            model=model,
            temperature=0.0,
            max_tokens=settings.llm_arb_max_tokens,
            json_mode=True,
        )
        parsed = _extract_json(raw)
    except Exception as exc:
        logger.warning("LLM arbitrage analysis failed: %s", exc)
        return {}

    results: dict[str, dict[str, Any]] = {}
    for item in parsed.get("opportunities") or []:
        if not isinstance(item, dict):
            continue
        event_id = str(item.get("event_id") or "")
        if not event_id:
            continue
        arb = _arb_from_llm_item(item)
        if arb is None:
            continue
        results[event_id] = {
            "arbitrage": arb,
            "reasoning": str(item.get("reasoning") or ""),
            "sources_used": list(item.get("sources_used") or []),
            "method": "llm",
        }
    return results


def filter_records_to_target_sources(records: list[UnifiedRecord]) -> list[UnifiedRecord]:
    """Keep only quotes from canonical target sources (mapped from Odds API keys)."""
    from target_sources import ODDS_API_KEY_TO_TARGET

    for record in records:
        filtered: dict[str, list] = {}
        for book_key, quotes in record.sources.items():
            canonical = ODDS_API_KEY_TO_TARGET.get(book_key, book_key)
            if canonical not in TARGET_SOURCE_BY_KEY:
                continue
            # Re-key to canonical target key
            for q in quotes:
                q.source = canonical
            if quotes:
                filtered.setdefault(canonical, []).extend(quotes)
        record.sources = filtered
        record.metadata["target_sources"] = list(filtered.keys())
    return records
