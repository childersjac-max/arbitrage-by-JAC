"""Perplexity Sonar — web-researched odds via structured JSON (replaces The Odds API)."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any

import httpx

from config import get_settings
from integrators.base import OddsIntegrator
from integrators.odds_events import event_dict_to_record
from models import UnifiedRecord
from target_sources import TARGET_SOURCES

logger = logging.getLogger(__name__)

SPORT_LABELS: dict[str, str] = {
    "basketball_nba": "NBA basketball",
    "basketball_ncaab": "NCAA men's basketball",
    "basketball_wnba": "WNBA basketball",
    "americanfootball_nfl": "NFL football",
    "americanfootball_ncaaf": "NCAA football",
    "baseball_mlb": "MLB baseball",
    "icehockey_nhl": "NHL hockey",
    "soccer_epl": "English Premier League soccer",
    "soccer_usa_mls": "MLS soccer",
    "mma_mixed_martial_arts": "MMA / UFC",
    "boxing_boxing": "boxing",
    "golf_pga": "PGA golf",
    "tennis_atp": "ATP tennis",
}

MARKET_LABELS: dict[str, str] = {
    "h2h": "moneyline (head-to-head)",
    "spreads": "point spread",
    "totals": "game total over/under",
}

ODDS_EVENTS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["events"],
    "properties": {
        "events": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["home_team", "away_team", "bookmakers"],
                "properties": {
                    "id": {"type": "string"},
                    "home_team": {"type": "string"},
                    "away_team": {"type": "string"},
                    "commence_time": {"type": ["string", "null"]},
                    "bookmakers": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["key", "markets"],
                            "properties": {
                                "key": {"type": "string"},
                                "markets": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "additionalProperties": False,
                                        "required": ["key", "outcomes"],
                                        "properties": {
                                            "key": {"type": "string"},
                                            "outcomes": {
                                                "type": "array",
                                                "items": {
                                                    "type": "object",
                                                    "additionalProperties": False,
                                                    "required": ["name", "price"],
                                                    "properties": {
                                                        "name": {"type": "string"},
                                                        "price": {"type": "number"},
                                                        "point": {"type": ["number", "null"]},
                                                    },
                                                },
                                            },
                                        },
                                    },
                                },
                            },
                        },
                    },
                },
            },
        }
    },
}


def _book_keys_for_prompt() -> str:
    keys = sorted({src.key for src in TARGET_SOURCES if not src.direct_only})
    return ", ".join(keys)


def _sport_label(sport_key: str) -> str:
    return SPORT_LABELS.get(sport_key, sport_key.replace("_", " "))


def _market_phrase(markets: list[str]) -> str:
    parts = [f"{m} ({MARKET_LABELS.get(m, m)})" for m in markets]
    return ", ".join(parts)


def _extract_json_payload(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if not cleaned.startswith("{"):
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            cleaned = cleaned[start : end + 1]
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    data = json.loads(cleaned)
    if not isinstance(data, dict):
        raise ValueError("Perplexity response JSON root must be an object")
    return data


class PerplexityOddsIntegrator(OddsIntegrator):
    name = "perplexity_odds"

    def __init__(self, *, client: httpx.AsyncClient | None = None) -> None:
        self._client = client
        self._owns_client = client is None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            settings = get_settings()
            self._client = httpx.AsyncClient(
                base_url=settings.perplexity_base_url.rstrip("/"),
                timeout=max(settings.http_timeout_sec, 90.0),
                headers={
                    "Authorization": f"Bearer {settings.perplexity_api_key}",
                    "Content-Type": "application/json",
                },
            )
        return self._client

    async def close(self) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    async def health_check(self) -> tuple[bool, str]:
        settings = get_settings()
        if not settings.perplexity_api_key:
            return False, "PERPLEXITY_API_KEY is not set"
        try:
            client = await self._get_client()
            resp = await client.post(
                "/chat/completions",
                json={
                    "model": settings.perplexity_model,
                    "max_tokens": 16,
                    "messages": [{"role": "user", "content": "Reply with exactly: ok"}],
                },
            )
            resp.raise_for_status()
            body = resp.json()
            content = (
                body.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )
            return True, f"OK (model={settings.perplexity_model}, reply={content[:20]!r})"
        except Exception as exc:
            return False, str(exc)

    async def fetch_records(
        self,
        sport_key: str,
        *,
        market_types: list[str] | None = None,
    ) -> list[UnifiedRecord]:
        settings = get_settings()
        if not settings.perplexity_api_key:
            raise RuntimeError("Set PERPLEXITY_API_KEY in harvester/.env or the environment")

        markets = market_types or [
            m.strip() for m in settings.odds_api_markets.split(",") if m.strip()
        ]
        if not markets:
            markets = ["h2h"]

        sport_label = _sport_label(sport_key)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        books = _book_keys_for_prompt()
        market_phrase = _market_phrase(markets)

        user_prompt = (
            f"Find up to 12 upcoming {sport_label} games from today ({today}) through the next 2 days. "
            f"For each scheduled game return {market_phrase} odds as DECIMAL numbers (e.g. 1.91, 2.10) "
            f"from US sportsbooks when available. Use these bookmaker keys exactly: {books}. "
            "Include home_team, away_team, commence_time in ISO8601 UTC when known, and "
            "for spreads/totals include the point on each outcome. "
            "Approximate lines from public aggregators are acceptable when live quotes "
            "are unavailable; only return an empty events array if no games are scheduled."
        )

        client = await self._get_client()
        resp = await client.post(
            "/chat/completions",
            json={
                "model": settings.perplexity_model,
                "max_tokens": settings.perplexity_max_tokens,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a sports odds researcher. Return JSON matching the schema. "
                            "Use decimal odds. Prefer verifiable public sportsbook or aggregator "
                            "data. Never omit scheduled games."
                        ),
                    },
                    {"role": "user", "content": user_prompt},
                ],
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "odds_events",
                        "schema": ODDS_EVENTS_SCHEMA,
                    },
                },
            },
        )
        resp.raise_for_status()
        body = resp.json()
        choice = body.get("choices", [{}])[0]
        content = choice.get("message", {}).get("content", "")
        if choice.get("finish_reason") == "length":
            logger.warning("Perplexity odds response truncated (max_tokens); retry with fewer markets")
        if not content:
            raise RuntimeError("Perplexity returned an empty completion")

        payload = _extract_json_payload(content)
        events = payload.get("events") or []
        if not isinstance(events, list):
            raise ValueError("Perplexity odds payload missing events array")

        records: list[UnifiedRecord] = []
        for item in events:
            if not isinstance(item, dict):
                continue
            records.append(
                event_dict_to_record(
                    item,
                    sport_key,
                    metadata_extra={
                        "odds_source": "perplexity",
                        "odds_research_note": "Web-researched via Perplexity Sonar; verify before betting.",
                    },
                )
            )

        logger.info(
            "Perplexity returned %s event(s) for %s markets=%s",
            len(records),
            sport_key,
            markets,
        )
        return records
