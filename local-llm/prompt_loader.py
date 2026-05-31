"""Load system prompts from prompts/*.txt files."""

from __future__ import annotations

import os

from paths import PACKAGE_DIR


def system_prompt_path() -> str:
    rel = os.getenv("LOCAL_LLM_SYSTEM_PROMPT_FILE", "prompts/system_default.txt")
    return str((PACKAGE_DIR / rel).resolve())


def get_default_system_prompt() -> str:
    """
    Default system prompt for chat / prompt_cli / web_app.

    Always reads the file fresh (no cache) so edits in Notepad apply after Reload.
    """
    from config import get_settings

    rel = os.getenv("LOCAL_LLM_SYSTEM_PROMPT_FILE", "prompts/system_default.txt")
    path = PACKAGE_DIR / rel
    if path.is_file():
        return path.read_text(encoding="utf-8").strip()

    return get_settings().local_llm_default_system


def get_system_prompt_info() -> tuple[str, str]:
    """Return (prompt text, human-readable source description)."""
    rel = os.getenv("LOCAL_LLM_SYSTEM_PROMPT_FILE", "prompts/system_default.txt")
    path = PACKAGE_DIR / rel
    if path.is_file():
        return path.read_text(encoding="utf-8").strip(), f"Loaded from `{path}`"
    from config import get_settings

    return (
        get_settings().local_llm_default_system,
        "Using `.env` → `LOCAL_LLM_DEFAULT_SYSTEM` (file not found). "
        f"Create `{path}` or copy from `prompts/system_default.txt`.",
    )


def load_prompt_file(relative_path: str) -> str:
    path = PACKAGE_DIR / relative_path
    if not path.is_file():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    return path.read_text(encoding="utf-8").strip()
