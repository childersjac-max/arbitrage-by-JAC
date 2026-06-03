"""
Integrator factory — one adapter per target platform (lawful sources only).

We do NOT implement stealth browser scraping or TLS-evasion here. Each adapter
either uses The Odds API (aggregated US books) or a documented official API stub.
"""

from __future__ import annotations

import logging
from typing import Any

from integrators.base import OddsIntegrator
from integrators.odds_api import OddsApiIntegrator
from integrators.stubs import STUB_INTEGRATORS, StubIntegrator
from target_sources import TARGET_SOURCES, TargetSource

logger = logging.getLogger(__name__)


class IntegratorFactory:
  """Registry and lifecycle for all 14 target platforms."""

  def __init__(self) -> None:
    self._odds_api = OddsApiIntegrator()
    self._stubs: dict[str, StubIntegrator] = dict(STUB_INTEGRATORS)

  def describe_sources(self) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for src in TARGET_SOURCES:
      rows.append(
        {
          "key": src.key,
          "name": src.name,
          "category": src.category,
          "channel": "odds_api" if not src.direct_only else "official_api_required",
          "odds_api_aliases": list(src.odds_api_keys),
          "integration_note": src.integration_note,
        }
      )
    return rows

  def odds_api_integrator(self) -> OddsApiIntegrator:
    return self._odds_api

  def stub(self, platform_key: str) -> StubIntegrator:
    return self._stubs[platform_key]

  def all_target_keys(self) -> list[str]:
    return [s.key for s in TARGET_SOURCES]

  def direct_only_sources(self) -> list[TargetSource]:
    return [s for s in TARGET_SOURCES if s.direct_only]

  async def close(self) -> None:
    await self._odds_api.close()
