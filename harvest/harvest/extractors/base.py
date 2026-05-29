"""Extractor contract and fallback layer tagging."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum

from harvest.models import MarketFragment


class FetchLayer(str, Enum):
    """Prioritized fallback matrix (compliant sources only)."""

    A_HTTP_API = "layer_a_http_api"
    B_OFFICIAL_SDK = "layer_b_official_sdk"
    C_CACHED = "layer_c_cached"
    DISABLED = "disabled"


class BaseExtractor(ABC):
    source_id: str
    layer: FetchLayer = FetchLayer.A_HTTP_API

    @abstractmethod
    def fetch(self) -> list[MarketFragment]:
        ...

    @property
    def is_configured(self) -> bool:
        return True
