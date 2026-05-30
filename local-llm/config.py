"""Configuration helpers for local Ollama-backed inference."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class LocalLLMConfig:
    """Local inference settings sourced from environment variables."""

    base_url: str = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    model: str = os.environ.get("OLLAMA_MODEL", "llama3.1")
    timeout_seconds: float = float(os.environ.get("LOCAL_LLM_TIMEOUT_SECONDS", "20"))
