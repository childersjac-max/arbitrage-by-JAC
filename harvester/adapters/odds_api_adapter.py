"""Aggregates US sportsbooks via the configured odds provider."""

from __future__ import annotations

from adapters.base import BaseFeedAdapter
from integrator_factory import IntegratorFactory
from llm_arbitrage import filter_records_to_target_sources
from models_depth import EventSnapshot
from odds_api_fetch import fetch_odds_api_multi_market
from settings import get_settings
from snapshot_builder import merge_records_to_events


class OddsApiFeedAdapter(BaseFeedAdapter):
  platform_key = "the_odds_api"
  display_name = "Odds gateway (Perplexity or The Odds API)"

  def __init__(self) -> None:
    self._factory = IntegratorFactory()

  async def health_check(self) -> tuple[bool, str]:
    return await self._factory.primary_odds_integrator().health_check()

  async def fetch_events(self, sport_key: str) -> list[EventSnapshot]:
    settings = get_settings()
    markets = [m.strip() for m in settings.odds_api_markets.split(",") if m.strip()]
    records = await fetch_odds_api_multi_market(self._factory, sport_key, markets)
    records = filter_records_to_target_sources(records)
    return merge_records_to_events(records)

  async def close(self) -> None:
    await self._factory.close()
