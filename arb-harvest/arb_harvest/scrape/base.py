"""Interface for supplemental (non–Odds API) data sources."""

from __future__ import annotations

from abc import ABC, abstractmethod

from arb_harvest.models import NormalizedEvent


class SupplementalFetcher(ABC):
    """Each fetcher returns zero or more partial events to splice into baseline."""

    source_id: str = "base"

    @abstractmethod
    def fetch(self) -> list[NormalizedEvent]:
        ...
