"""Helpers to verify Ollama is reachable before prompting."""

from __future__ import annotations

import httpx

from config import get_settings


def format_connection_help(exc: BaseException | None = None) -> str:
    settings = get_settings()
    host = settings.ollama_host
    model = settings.ollama_model
    lines = [
        "Could not reach your local LLM server.",
        "",
        "Fix checklist:",
        f"  1. Start Ollama (Windows tray icon or open Ollama from Start menu)",
        f"  2. Test in Git Bash: curl {host}/api/tags",
        f"  3. Pull the model: ollama pull {model}",
        f"     (or full path on Windows:)",
        f'     "/c/Users/child/AppData/Local/Programs/Ollama/ollama.exe" pull {model}',
        f"  4. Confirm .env OLLAMA_HOST={host} and OLLAMA_MODEL={model}",
        "",
        "First prompt after reboot can take 1-3 minutes while the model loads into RAM.",
        "If it times out, set LOCAL_LLM_PROMPT_TIMEOUT_SEC=600 in .env",
    ]
    if exc:
        lines.extend(["", f"Technical detail: {exc}"])
    return "\n".join(lines)


async def check_ollama_reachable() -> tuple[bool, str]:
    settings = get_settings()
    url = f"{settings.ollama_host.rstrip('/')}/api/tags"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url)
            r.raise_for_status()
            data = r.json()
            names = [m.get("name", "") for m in data.get("models", [])]
            if settings.ollama_model.split(":")[0] not in " ".join(names):
                return False, (
                    f"Ollama is running but model '{settings.ollama_model}' may not be pulled.\n"
                    f"Run: ollama pull {settings.ollama_model}\n"
                    f"Installed models: {', '.join(names) or '(none)'}"
                )
            return True, "OK"
    except Exception as exc:
        return False, format_connection_help(exc)
