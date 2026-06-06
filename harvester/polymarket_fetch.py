"""Fetch Polymarket records via integrator factory."""

from __future__ import annotations

import logging

from integrator_factory import IntegratorFactory
from models import UnifiedRecord
from settings import get_settings

logger = logging.getLogger(__name__)


async def fetch_polymarket_records(
    factory: IntegratorFactory,
    sport_key: str,
) -> list[UnifiedRecord]:
    settings = get_settings()
    if not settings.polymarket_enabled:
        return []
    try:
        return await factory.polymarket_integrator().fetch_records(sport_key)
    except Exception as exc:
        logger.warning("Polymarket fetch failed: %s", exc)
        raise
