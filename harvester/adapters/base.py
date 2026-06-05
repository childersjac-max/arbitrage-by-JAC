"""Abstract adapter for a single target platform."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from models_depth import EventSnapshot


class BaseFeedAdapter(ABC):
  """Lawful data feed adapter — implement using documented APIs only."""

  platform_key: str
  display_name: str

  @abstractmethod
  async def health_check(self) -> tuple[bool, str]:
    ...

  @abstractmethod
  async def fetch_events(self, sport_key: str) -> list[EventSnapshot]:
    ...

  def integration_note(self) -> dict[str, Any]:
    return {"platform": self.platform_key, "channel": "official_api"}
