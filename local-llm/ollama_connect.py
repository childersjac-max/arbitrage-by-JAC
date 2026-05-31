"""
Reliable Ollama connectivity for Windows (retries, host fallback, urllib backup).
"""

from __future__ import annotations

import asyncio
import json
import logging
import urllib.error
import urllib.request
from typing import Any

import httpx

from config import get_settings
from paths import ENV_FILE

logger = logging.getLogger(__name__)

_resolved_host: str | None = None
_cached_models: list[str] | None = None


def _format_error(exc: BaseException | None) -> str:
    if exc is None:
        return "unknown error"
    text = str(exc).strip()
    if text:
        return f"{type(exc).__name__}: {text}"
    return f"{type(exc).__name__} ({repr(exc)})"


def format_connection_help(exc: BaseException | None = None) -> str:
    settings = get_settings()
    host = _resolved_host or settings.ollama_host
    model = settings.ollama_model
    env_hint = f"Config file: `{ENV_FILE}`" if ENV_FILE.is_file() else (
        f"No `.env` at `{ENV_FILE}`"
    )
    lines = [
        "Could not reach Ollama.",
        "",
        env_hint,
        "",
        "**Do this (in order):**",
        "1. Open **Ollama** from the Start menu — wait until the whale icon shows in the tray.",
        "2. In Git Bash run: `curl http://127.0.0.1:11434/api/tags`",
        "   You must see JSON, not `Connection refused`.",
        f"3. If needed: `ollama pull {model}`",
        "",
        f"Expected: `OLLAMA_HOST={settings.ollama_host}` · `OLLAMA_MODEL={model}`",
        "",
        "First chat after reboot can take 1–3 minutes while the model loads into RAM.",
    ]
    if exc is not None:
        lines.extend(["", f"**Technical:** {_format_error(exc)}"])
    return "\n".join(lines)


def candidate_hosts() -> list[str]:
    configured = get_settings().ollama_host.rstrip("/")
    return list(
        dict.fromkeys(
            [
                configured,
                "http://127.0.0.1:11434",
                "http://localhost:11434",
            ]
        )
    )


def _parse_tags_json(data: dict[str, Any]) -> list[str]:
    return [str(m.get("name", "")) for m in data.get("models", []) if m.get("name")]


def _fetch_tags_urllib(host: str) -> list[str]:
    url = f"{host.rstrip('/')}/api/tags"
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return _parse_tags_json(data)


async def _fetch_tags_httpx(host: str) -> list[str]:
    url = f"{host.rstrip('/')}/api/tags"
    timeout = httpx.Timeout(60.0, connect=30.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.get(url)
        r.raise_for_status()
        return _parse_tags_json(r.json())


def pick_ollama_model(requested: str, installed: list[str]) -> str:
    if not installed:
        return requested
    if requested in installed:
        return requested
    base = requested.split(":")[0]
    for name in installed:
        if name.startswith(f"{base}:") or name == base:
            return name
    return installed[0]


def model_is_installed(requested: str, installed: list[str]) -> bool:
    if not installed:
        return False
    if requested in installed:
        return True
    base = requested.split(":")[0]
    return any(
        n == requested or n.startswith(f"{base}:") or n.startswith(base) for n in installed
    )


async def resolve_ollama(*, force: bool = False) -> tuple[str, list[str]]:
    """Find a working Ollama host and cache it for this process."""
    global _resolved_host, _cached_models

    if not force and _resolved_host and _cached_models is not None:
        return _resolved_host, _cached_models

    last_exc: BaseException | None = None
    for host in candidate_hosts():
        for attempt in range(4):
            try:
                names = await _fetch_tags_httpx(host)
                _resolved_host = host.rstrip("/")
                _cached_models = names
                logger.info("Ollama OK at %s (%d models)", _resolved_host, len(names))
                return _resolved_host, names
            except Exception as exc:
                last_exc = exc
                logger.debug("httpx tags failed %s attempt %s: %s", host, attempt + 1, exc)
                try:
                    names = await asyncio.to_thread(_fetch_tags_urllib, host)
                    _resolved_host = host.rstrip("/")
                    _cached_models = names
                    logger.info("Ollama OK (urllib) at %s", _resolved_host)
                    return _resolved_host, names
                except Exception as exc2:
                    last_exc = exc2
                    logger.debug("urllib tags failed %s: %s", host, exc2)
            await asyncio.sleep(1.5 * (attempt + 1))

    _resolved_host = None
    _cached_models = None
    raise ConnectionError(format_connection_help(last_exc))


def get_ollama_base_url() -> str:
    if _resolved_host:
        return _resolved_host
    return get_settings().ollama_host.rstrip("/")


async def get_effective_ollama_model() -> str:
    _, names = await resolve_ollama()
    return pick_ollama_model(get_settings().ollama_model, names)


async def check_ollama_reachable() -> tuple[bool, str]:
    settings = get_settings()
    try:
        host, names = await resolve_ollama()
    except ConnectionError as exc:
        return False, str(exc)
    except Exception as exc:
        return False, format_connection_help(exc)

    requested = settings.ollama_model
    if not names:
        return False, (
            f"Ollama at {host} has **no models**. Run: `ollama pull {requested}`"
        )
    if not model_is_installed(requested, names):
        effective = pick_ollama_model(requested, names)
        return False, (
            f"Model `{requested}` not found.\n\n"
            f"Installed: {', '.join(names)}\n\n"
            f"Run: `ollama pull {requested}`\n"
            f"Or set `OLLAMA_MODEL={effective}` in `.env`"
        )
    effective = pick_ollama_model(requested, names)
    if effective != requested:
        return True, f"OK at {host} (using `{effective}`)"
    return True, f"OK at {host}"


async def warmup_ollama() -> tuple[bool, str]:
    """Ping Ollama before first chat (loads connection + validates model)."""
    try:
        host, names = await resolve_ollama(force=True)
        model = pick_ollama_model(get_settings().ollama_model, names)
        return True, f"Ready at {host} · model `{model}`"
    except Exception as exc:
        return False, format_connection_help(exc)
