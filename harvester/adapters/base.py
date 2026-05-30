"""Adapter interfaces and source-specific error types."""

from __future__ import annotations

from abc import ABC, abstractmethod

from harvester.models import AdapterFetchResult, SourceQuote


class SourceAdapterError(Exception):
    """Base class for adapter failures."""


class SourceTransientError(SourceAdapterError):
    """Retryable adapter error for HTTP 429 and 5xx responses."""


class SourceUnavailableError(SourceAdapterError):
    """Raised when a source has no compliant integration path configured."""


class SourceAdapter(ABC):
    """Abstract interface shared by every data source adapter."""

    source_id: str

    @abstractmethod
    async def fetch_quotes(self) -> AdapterFetchResult:
        """Fetch current quotes and return canonical source records."""


class NotImplementedSourceAdapter(SourceAdapter):
    """Compliant stub for sources without licensed or documented API access."""

    def __init__(self, source_id: str, reason: str) -> None:
        self.source_id = source_id
        self.reason = reason

    async def fetch_quotes(self) -> AdapterFetchResult:
        """Return a structured empty payload and mark the source unavailable."""

        return AdapterFetchResult(
            source_id=self.source_id,
            quotes=[],
            status="source_unavailable",
            message=self.reason,
        )


def empty_fetch_result(source_id: str, quotes: list[SourceQuote] | None = None) -> AdapterFetchResult:
    """Build a successful adapter result with an optional quote list."""

    return AdapterFetchResult(source_id=source_id, quotes=quotes or [], status="ok")
