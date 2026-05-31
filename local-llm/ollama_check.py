"""Helpers to verify Ollama is reachable before prompting."""

from __future__ import annotations

import asyncio

import httpx

from config import get_settings
from paths import ENV_FILE


def format_connection_help(exc: BaseException | None = None) -> str:
    settings = get_settings()
    host = settings.ollama_host
    model = settings.ollama_model
    env_hint = f"Config file: `{ENV_FILE}`" if ENV_FILE.is_file() else (
        f"No `.env` found at `{ENV_FILE}` — copy `.env.example` to `.env`."
    )
    lines = [
        "Could not reach Ollama.",
        "",
        env_hint,
        "",
        "**Do this:**",
        "1. Open **Ollama** from the Start menu (whale icon in the system tray).",
        f"2. In Git Bash, test: `curl {host}/api/tags`",
        f"3. Pull your model: `ollama pull {model}`",
        "",
        f"Your app expects: `OLLAMA_HOST={host}` and `OLLAMA_MODEL={model}`",
        "",
        "First message after reboot can take 1–3 minutes while the model loads.",
    ]
    if exc:
        lines.extend(["", f"**Error:** `{exc}`"])
    return "\n".join(lines)


def model_is_installed(requested: str, installed: list[str]) -> bool:
    if not installed:
        return False
    if requested in installed:
        return True
    base = requested.split(":")[0]
    return any(n == requested or n.startswith(f"{base}:") or n.startswith(base) for n in installed)


def pick_ollama_model(requested: str, installed: list[str]) -> str:
    """Use requested tag if present, else closest match, else first installed."""
    if not installed:
        return requested
    if requested in installed:
        return requested
    base = requested.split(":")[0]
    for name in installed:
        if name.startswith(f"{base}:") or name == base:
            return name
    return installed[0]


async def fetch_installed_models(host: str) -> list[str]:
    url = f"{host.rstrip('/')}/api/tags"
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                r = await client.get(url)
                r.raise_for_status()
                data = r.json()
                return [str(m.get("name", "")) for m in data.get("models", []) if m.get("name")]
        except Exception as exc:
            last_exc = exc
            if attempt < 2:
                await asyncio.sleep(1.0)
    raise last_exc or RuntimeError("unknown error")


async def check_ollama_reachable() -> tuple[bool, str]:
    settings = get_settings()
    host = settings.ollama_host.rstrip("/")
    requested = settings.ollama_model

    try:
        names = await fetch_installed_models(host)
    except Exception as exc:
        return False, format_connection_help(exc)

    if not names:
        return False, (
            f"Ollama is running at {host} but **no models** are installed.\n\n"
            f"Run: `ollama pull {requested}`"
        )

    if not model_is_installed(requested, names):
        effective = pick_ollama_model(requested, names)
        return False, (
            f"Ollama is running, but `{requested}` is not installed.\n\n"
            f"Installed: {', '.join(names)}\n\n"
            f"Run: `ollama pull {requested}`\n"
            f"Or set in `.env`: `OLLAMA_MODEL={effective}`"
        )

    effective = pick_ollama_model(requested, names)
    if effective != requested:
        return True, f"OK (using model `{effective}`)"
    return True, "OK"


async def get_effective_ollama_model() -> str:
    """Model name to send to Ollama API (must exist locally)."""
    settings = get_settings()
    names = await fetch_installed_models(settings.ollama_host)
    return pick_ollama_model(settings.ollama_model, names)
