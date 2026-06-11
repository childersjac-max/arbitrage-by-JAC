"""Aggregates US sportsbooks via The Odds API."""

from __future__ import annotations

from adapters.base import BaseFeedAdapter
from integrator_factory import IntegratorFactory
from llm_arbitrage import filter_records_to_target_sources
from models_depth import EventSnapshot
from odds_api_fetch import fetch_sport_odds
from settings import get_settings
from snapshot_builder import merge_records_to_events


class OddsApiFeedAdapter(BaseFeedAdapter):
  platform_key = "the_odds_api"
  display_name = "The Odds API (US books aggregate)"

  def __init__(self) -> None:
    self._factory = IntegratorFactory()

  async def health_check(self) -> tuple[bool, str]:
    return await self._factory.odds_api_integrator().health_check()

  async def fetch_events(self, sport_key: str) -> list[EventSnapshot]:
    records = await fetch_sport_odds(self._factory, sport_key)
    records = filter_records_to_target_sources(records)
    return merge_records_to_events(records)

  async def close(self) -> None:
    await self._factory.close()
