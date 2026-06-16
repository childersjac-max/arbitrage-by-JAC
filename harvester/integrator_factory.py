"""
Integrator factory — one adapter per target platform (lawful sources only).

We do NOT implement stealth browser scraping or TLS-evasion here. Each adapter
either uses Perplexity Sonar (web-researched odds), The Odds API (aggregated US
books), or a documented official API stub.
"""

from __future__ import annotations

import logging
from typing import Any

from config import get_settings
from integrators.base import OddsIntegrator
from integrators.odds_api import OddsApiIntegrator
from integrators.perplexity_odds import PerplexityOddsIntegrator
from integrators.stubs import STUB_INTEGRATORS, StubIntegrator
from target_sources import TARGET_SOURCES, TargetSource

logger = logging.getLogger(__name__)


class IntegratorFactory:
  """Registry and lifecycle for all 14 target platforms."""

  def __init__(self) -> None:
    self._odds_api = OddsApiIntegrator()
    self._perplexity = PerplexityOddsIntegrator()
    self._stubs: dict[str, StubIntegrator] = dict(STUB_INTEGRATORS)

  def describe_sources(self) -> list[dict[str, Any]]:
    settings = get_settings()
    channel = (
      "perplexity"
      if settings.effective_odds_provider() == "perplexity"
      else "odds_api"
    )
    rows: list[dict[str, Any]] = []
    for src in TARGET_SOURCES:
      rows.append(
        {
          "key": src.key,
          "name": src.name,
          "category": src.category,
          "channel": "official_api_required" if src.direct_only else channel,
          "odds_api_aliases": list(src.odds_api_keys),
          "integration_note": src.integration_note,
        }
      )
    return rows

  def primary_odds_integrator(self) -> OddsIntegrator:
    settings = get_settings()
    if settings.effective_odds_provider() == "perplexity":
      return self._perplexity
    return self._odds_api

  def odds_api_integrator(self) -> OddsApiIntegrator:
    return self._odds_api

  def perplexity_integrator(self) -> PerplexityOddsIntegrator:
    return self._perplexity

  def stub(self, platform_key: str) -> StubIntegrator:
    return self._stubs[platform_key]

  def all_target_keys(self) -> list[str]:
    return [s.key for s in TARGET_SOURCES]

  def direct_only_sources(self) -> list[TargetSource]:
    return [s for s in TARGET_SOURCES if s.direct_only]

  async def close(self) -> None:
    await self._odds_api.close()
    await self._perplexity.close()
