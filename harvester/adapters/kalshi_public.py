"""Kalshi adapter placeholder.

Kalshi exposes documented APIs, but production event-market usage depends on
account, market-data, and exchange terms that should be reviewed before live
integration. This module deliberately returns a structured unavailable result
until licensed access and approved endpoint usage are configured.
"""

from harvester.adapters.base import NotImplementedSourceAdapter


class KalshiPublicAdapter(NotImplementedSourceAdapter):
    """Compliant stub for future Kalshi public/API integration."""

    def __init__(self) -> None:
        super().__init__(
            source_id="kalshi_public",
            reason=(
                "source_unavailable: Kalshi integration requires confirming documented "
                "API terms and any required licensed credentials before use."
            ),
        )
