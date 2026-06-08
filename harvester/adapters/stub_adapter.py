"""Placeholder for platforms requiring a separate official API key."""

from __future__ import annotations

from adapters.base import BaseFeedAdapter
from models_depth import EventSnapshot
from target_sources import TARGET_SOURCE_BY_KEY


class OfficialApiStubAdapter(BaseFeedAdapter):
  def __init__(self, platform_key: str) -> None:
    src = TARGET_SOURCE_BY_KEY[platform_key]
    self.platform_key = platform_key
    self.display_name = src.name
    self._note = src.integration_note

  async def health_check(self) -> tuple[bool, str]:
    return False, self._note

  async def fetch_events(self, sport_key: str) -> list[EventSnapshot]:
    raise NotImplementedError(
      f"{self.display_name} requires an official API integration: {self._note}"
    )

  def integration_note(self) -> dict:
    return {
      "platform": self.platform_key,
      "channel": "official_api_required",
      "note": self._note,
    }
