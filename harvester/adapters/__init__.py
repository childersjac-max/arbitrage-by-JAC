"""Platform adapters (official APIs + Odds API aggregation)."""

from adapters.base import BaseFeedAdapter
from adapters.registry import AdapterRegistry

__all__ = ["BaseFeedAdapter", "AdapterRegistry"]
