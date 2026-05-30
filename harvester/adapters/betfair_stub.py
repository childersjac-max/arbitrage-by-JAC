"""Betfair source stub.

Betfair exchange data requires licensed API credentials and acceptance of the
provider's terms. No unauthenticated or hidden endpoints are used here.
"""

from harvester.adapters.base import NotImplementedSourceAdapter


class BetfairStubAdapter(NotImplementedSourceAdapter):
    """Structured empty adapter until licensed Betfair credentials are supplied."""

    def __init__(self) -> None:
        super().__init__(
            source_id="betfair",
            reason="source_unavailable: Betfair requires licensed API credentials.",
        )
