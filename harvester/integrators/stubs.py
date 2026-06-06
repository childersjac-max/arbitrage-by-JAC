"""Lawful placeholder integrators — derived from target_sources registry."""

from __future__ import annotations

from typing import Any

from integrators.base import OddsIntegrator
from models import UnifiedRecord
from target_sources import TARGET_SOURCES

# Platforms with live integrators in integrators/ — not stubs.
_LIVE_DIRECT_KEYS = frozenset({"polymarket"})

STUB_SPECS: list[tuple[str, str]] = [
    (s.key, s.integration_note or f"Direct adapter for {s.name} not implemented.")
    for s in TARGET_SOURCES
    if s.direct_only and s.key not in _LIVE_DIRECT_KEYS
]


class StubIntegrator(OddsIntegrator):
    def __init__(self, platform_key: str, todo: str) -> None:
        self.name = platform_key
        self._todo = todo

    async def fetch_records(
        self,
        sport_key: str,
        *,
        market_types: list[str] | None = None,
    ) -> list[UnifiedRecord]:
        raise NotImplementedError(
            f"{self.name} adapter is not implemented. Integration path: {self._todo}"
        )

    async def health_check(self) -> tuple[bool, str]:
        return False, f"stub only — {self._todo}"

    def integration_notes(self) -> dict[str, Any]:
        return {
            "integrator": self.name,
            "status": "stub",
            "integration_path": self._todo,
        }


def get_stub_integrator(platform_key: str) -> StubIntegrator:
    for key, todo in STUB_SPECS:
        if key == platform_key:
            return StubIntegrator(key, todo)
    raise KeyError(f"Unknown stub platform: {platform_key}")


STUB_INTEGRATORS: dict[str, StubIntegrator] = {
    key: StubIntegrator(key, todo) for key, todo in STUB_SPECS
}
