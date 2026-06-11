"""Resolve sports-arbitrage project paths and inject context into multi-agent prompts."""

from __future__ import annotations

import os
import socket
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent
PROMPTS_REPO = REPO_ROOT / "prompts"
LOCAL_OVERRIDE = ROOT / "prompts" / "project_context.txt"


def _lan_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except OSError:
        return "192.168.1.100"


def resolve_project_root() -> Path:
    env = os.environ.get("PROJECT_ROOT", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return REPO_ROOT.resolve()


@lru_cache(maxsize=1)
def default_urls() -> dict[str, str]:
    llm_port = os.environ.get("LOCAL_LLM_UI_PORT", "7860")
    harvester_port = os.environ.get("HARVESTER_UI_PORT", "8765")
    lan_ip = os.environ.get("LAN_IP", _lan_ip())
    return {
        "APP_URL_LOCAL_LLM": os.environ.get("APP_URL_LOCAL_LLM", f"http://127.0.0.1:{llm_port}"),
        "APP_URL_LOCAL_LLM_LAN": os.environ.get(
            "APP_URL_LOCAL_LLM_LAN", f"http://{lan_ip}:{llm_port}"
        ),
        "APP_URL_HARVESTER": os.environ.get(
            "APP_URL_HARVESTER", f"http://127.0.0.1:{harvester_port}"
        ),
        "APP_URL_PUBLIC": os.environ.get("APP_URL_PUBLIC", ""),
        "PROJECT_ROOT_BASH": os.environ.get(
            "PROJECT_ROOT_BASH", "~/Projects/arbitrage-by-JAC"
        ),
        "PROJECT_ROOT_WIN": os.environ.get(
            "PROJECT_ROOT_WIN", r"C:\Users\child\Projects\arbitrage-by-JAC"
        ),
    }


def _load_context_template() -> str:
    candidates = [
        LOCAL_OVERRIDE,
        PROMPTS_REPO / "PROJECT_CONTEXT.txt",
        ROOT / "prompts" / "project_context.txt",
    ]
    for path in candidates:
        if path.is_file():
            return path.read_text(encoding="utf-8").strip()
    return (
        "Project: arbitrage-by-JAC sports arbitrage. "
        "Repo root: ~/Projects/arbitrage-by-JAC. "
        "Never invent stealth scrapers."
    )


def _load_file_map() -> str:
    path = PROMPTS_REPO / "PROJECT_FILE_MAP.txt"
    if path.is_file():
        return path.read_text(encoding="utf-8").strip()
    return ""


def project_context_block(*, include_file_map: bool | None = None) -> str:
    """Full context string prepended to planner/coder/reviewer system prompts."""
    if os.environ.get("INJECT_PROJECT_CONTEXT", "1").strip().lower() in ("0", "false", "no"):
        return ""

    urls = default_urls()
    body = _load_context_template()
    for key, value in urls.items():
        body = body.replace(key, value or "(not set)")

    if include_file_map is None:
        include_file_map = os.environ.get("INJECT_FILE_MAP", "1").strip().lower() not in (
            "0",
            "false",
            "no",
        )

    if include_file_map:
        file_map = _load_file_map()
        if file_map:
            for key, value in urls.items():
                file_map = file_map.replace(key, value or "(not set)")
            body = f"{body}\n\n## FILE MAP\n{file_map}"

    return body.strip()


def with_project_context(system_prompt: str) -> str:
    ctx = project_context_block()
    if not ctx:
        return system_prompt
    return f"{ctx}\n\n---\n\n{system_prompt}"
