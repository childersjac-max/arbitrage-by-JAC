"""Load sports-arbitrage project context for Gradio chat (single + multi-agent)."""

from __future__ import annotations

import os
import sys
from functools import lru_cache
from pathlib import Path

from paths import PACKAGE_DIR

REPO_ROOT = PACKAGE_DIR.parent
_MULTI_AGENT = REPO_ROOT / "multi-agent-llm"


def _ensure_multi_agent_path() -> None:
    path = str(_MULTI_AGENT.resolve())
    if _MULTI_AGENT.is_dir() and path not in sys.path:
        sys.path.insert(0, path)


@lru_cache(maxsize=1)
def project_context_for_chat() -> str:
    if os.environ.get("INJECT_PROJECT_CONTEXT_IN_CHAT", "1").strip().lower() in (
        "0",
        "false",
        "no",
    ):
        return ""
    _ensure_multi_agent_path()
    try:
        from project_context import project_context_block

        return project_context_block()
    except ImportError:
        path = REPO_ROOT / "prompts" / "PROJECT_CONTEXT.txt"
        if path.is_file():
            return path.read_text(encoding="utf-8").strip()
        return ""


def prepend_project_context(system_prompt: str) -> str:
    ctx = project_context_for_chat()
    if not ctx:
        return system_prompt
    return f"{ctx}\n\n---\n\n{system_prompt}"
