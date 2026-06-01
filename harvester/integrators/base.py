"""Abstract integrator contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from models import UnifiedRecord


class OddsIntegrator(ABC):
    """Fetch odds from one platform and return unified records."""

    name: str

    @abstractmethod
    async def fetch_records(
        self,
        sport_key: str,
        *,
        market_types: list[str] | None = None,
    ) -> list[UnifiedRecord]:
        """Return normalized-ready records for the given sport."""

    async def health_check(self) -> tuple[bool, str]:
        return True, "ok"

    def integration_notes(self) -> dict[str, Any]:
        return {"integrator": self.name, "status": "unknown"}
