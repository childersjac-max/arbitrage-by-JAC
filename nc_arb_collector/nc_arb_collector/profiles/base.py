"""Base class for modular extraction profiles."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..config import CollectorConfig
from ..http.client import ResilientHttpClient
from ..models import MarketPacket


class ExtractionProfile(ABC):
    platform_key: str
    display_name: str

    def __init__(self, config: CollectorConfig, http: ResilientHttpClient):
        self.config = config
        self.http = http

    @abstractmethod
    def extract(self, sport_keys: tuple[str, ...] | None = None) -> list[MarketPacket]:
        ...

    def __repr__(self) -> str:
        return f"<Profile {self.platform_key}>"
