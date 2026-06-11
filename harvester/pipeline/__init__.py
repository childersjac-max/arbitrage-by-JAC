"""Alignment and JSON stream output."""

from pipeline.align import align_events
from pipeline.stream import yield_differential_records

__all__ = ["align_events", "yield_differential_records"]
