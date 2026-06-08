"""Factory registry for all 14 target adapters."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from adapters.base import BaseFeedAdapter
from adapters.odds_api_adapter import OddsApiFeedAdapter
from adapters.stub_adapter import OfficialApiStubAdapter
from target_sources import TARGET_SOURCES

logger = logging.getLogger(__name__)


class AdapterRegistry:
  def __init__(self) -> None:
    self._odds = OddsApiFeedAdapter()
    self._stubs: dict[str, OfficialApiStubAdapter] = {
      s.key: OfficialApiStubAdapter(s.key) for s in TARGET_SOURCES if s.direct_only
    }

  def list_adapters(self) -> list[BaseFeedAdapter]:
    return [self._odds, *self._stubs.values()]

  def get(self, platform_key: str) -> BaseFeedAdapter:
    if platform_key == "the_odds_api":
      return self._odds
    if platform_key in self._stubs:
      return self._stubs[platform_key]
    raise KeyError(platform_key)

  async def fetch_all_lawful(self, sport_key: str) -> dict[str, Any]:
    """Concurrent fetch from Odds API; stubs return metadata only."""
    results: dict[str, Any] = {"events": [], "errors": [], "stubs": []}

    try:
      events = await self._odds.fetch_events(sport_key)
      results["events"] = [e.model_dump(mode="json") for e in events]
    except Exception as exc:
      logger.exception("Odds API fetch failed")
      results["errors"].append(str(exc))
    finally:
      await self._odds.close()

    for key, stub in self._stubs.items():
      results["stubs"].append(stub.integration_note())

    return results

  async def gather_events(self, sport_key: str) -> list:
    from models_depth import EventSnapshot

    out: list[EventSnapshot] = []
    data = await self.fetch_all_lawful(sport_key)
    for raw in data.get("events") or []:
      out.append(EventSnapshot.model_validate(raw))
    return out
