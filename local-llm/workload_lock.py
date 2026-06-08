"""Serialize Ollama requests so chat, normalization, and architect do not contend on CPU."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from enum import Enum

logger = logging.getLogger(__name__)

_ollama_lock = asyncio.Lock()
_active: str | None = None


class WorkloadKind(str, Enum):
    CHAT = "chat"
    MULTI_AGENT = "multi_agent"
    NORMALIZE = "normalize"
    ARCHITECT = "architect"
    WARMUP = "warmup"


@asynccontextmanager
async def ollama_workload(kind: WorkloadKind) -> AsyncIterator[None]:
    """
    Only one Ollama inference runs at a time (critical on CPU-only Windows).
    """
    global _active
    logger.debug("Waiting for Ollama lock (%s)", kind.value)
    async with _ollama_lock:
        prev = _active
        _active = kind.value
        if prev and prev != kind.value:
            logger.info("Ollama lock: %s → %s", prev, kind.value)
        try:
            yield
        finally:
            _active = prev


def active_workload() -> str | None:
    return _active
