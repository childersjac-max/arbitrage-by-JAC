"""Load system prompts from prompts/*.txt files."""

from __future__ import annotations

import os
from functools import lru_cache

from paths import PACKAGE_DIR


@lru_cache
def get_default_system_prompt() -> str:
    """
    Default system prompt for chat / prompt_cli / web_app.

    Priority:
      1. File at LOCAL_LLM_SYSTEM_PROMPT_FILE (relative to local-llm/)
      2. prompts/system_default.txt
      3. LOCAL_LLM_DEFAULT_SYSTEM from .env / config fallback
    """
    from config import get_settings

    rel = os.getenv("LOCAL_LLM_SYSTEM_PROMPT_FILE", "prompts/system_default.txt")
    path = PACKAGE_DIR / rel
    if path.is_file():
        return path.read_text(encoding="utf-8").strip()

    return get_settings().local_llm_default_system


def load_prompt_file(relative_path: str) -> str:
    path = PACKAGE_DIR / relative_path
    if not path.is_file():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    return path.read_text(encoding="utf-8").strip()
