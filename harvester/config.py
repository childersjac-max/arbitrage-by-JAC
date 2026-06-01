"""Backward-compatible shim — use settings.py (avoids clashing with local-llm/config.py)."""

from settings import HarvesterSettings, get_settings

__all__ = ["HarvesterSettings", "get_settings"]
