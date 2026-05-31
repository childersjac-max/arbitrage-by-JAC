"""
Reliable Ollama connectivity (Windows-friendly: urllib first, no proxy env).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any

import httpx

from config import get_settings
from paths import ENV_FILE

logger = logging.getLogger(__name__)

_resolved_host: str | None = None
_cached_models: list[str] | None = None
_prefer_urllib: bool = os.name == "nt"  # Windows: curl works; httpx often breaks via proxy


def httpx_client(**kwargs: Any) -> httpx.AsyncClient:
    """Localhost client — ignore HTTP_PROXY / HTTPS_PROXY (common Windows issue)."""
    return httpx.AsyncClient(trust_env=False, **kwargs)


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
    env_hint = f"Config file: `{ENV_FILE}`" if ENV_FILE.is_file() else f"No `.env` at `{ENV_FILE}`"
    lines = [
        "Could not reach Ollama from Python.",
        "",
        env_hint,
        "",
        "**If `curl http://127.0.0.1:11434/api/tags` works in Git Bash:**",
        "1. Keep the **Ollama** app open.",
        "2. **Restart** the web app: Ctrl+C, then `python web_app.py`.",
        "3. Click **Wake up Ollama** again.",
        "",
        "**If `curl` fails too:**",
        "1. Open Ollama from the Start menu.",
        f"2. Run: `ollama pull {model}`",
        "",
        f"Expected: `OLLAMA_HOST={settings.ollama_host}` · `OLLAMA_MODEL={model}`",
    ]
    if exc is not None:
        lines.extend(["", f"**Technical:** {_format_error(exc)}"])
    return "\n".join(lines)


def candidate_hosts() -> list[str]:
    configured = get_settings().ollama_host.rstrip("/")
    return list(
        dict.fromkeys([configured, "http://127.0.0.1:11434", "http://localhost:11434"])
    )


def _parse_tags_json(data: dict[str, Any]) -> list[str]:
    return [str(m.get("name", "")) for m in data.get("models", []) if m.get("name")]


def _fetch_tags_urllib(host: str) -> list[str]:
    url = f"{host.rstrip('/')}/api/tags"
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return _parse_tags_json(data)


def _chat_urllib(host: str, body: dict[str, Any]) -> str:
    url = f"{host.rstrip('/')}/api/chat"
    payload = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=600) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return str(data.get("message", {}).get("content", ""))


async def _fetch_tags_httpx(host: str) -> list[str]:
    url = f"{host.rstrip('/')}/api/tags"
    timeout = httpx.Timeout(60.0, connect=30.0)
    async with httpx_client(timeout=timeout) as client:
        r = await client.get(url)
        r.raise_for_status()
        return _parse_tags_json(r.json())


async def _try_tags(host: str) -> list[str]:
    global _prefer_urllib
    errors: list[BaseException] = []

    if _prefer_urllib:
        try:
            return await asyncio.to_thread(_fetch_tags_urllib, host)
        except Exception as exc:
            errors.append(exc)
            logger.warning("urllib tags failed: %s", exc)

    try:
        names = await _fetch_tags_httpx(host)
        return names
    except Exception as exc:
        errors.append(exc)
        logger.warning("httpx tags failed: %s", exc)

    try:
        names = await asyncio.to_thread(_fetch_tags_urllib, host)
        _prefer_urllib = True
        return names
    except Exception as exc:
        errors.append(exc)
        raise errors[-1] from exc


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
    global _resolved_host, _cached_models

    if not force and _resolved_host and _cached_models is not None:
        return _resolved_host, _cached_models

    last_exc: BaseException | None = None
    for host in candidate_hosts():
        for attempt in range(3):
            try:
                names = await _try_tags(host)
                _resolved_host = host.rstrip("/")
                _cached_models = names
                logger.info("Ollama OK at %s (%d models)", _resolved_host, len(names))
                return _resolved_host, names
            except Exception as exc:
                last_exc = exc
                await asyncio.sleep(1.0 * (attempt + 1))

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


async def ollama_chat_completion(
    messages: list[dict[str, str]],
    *,
    model: str,
    temperature: float,
    max_tokens: int,
    json_mode: bool = False,
) -> str:
    """
    POST /api/chat — urllib on Windows (same stack as working curl), httpx as backup.
    """
    global _prefer_urllib
    host = get_ollama_base_url()
    await resolve_ollama()

    body: dict[str, Any] = {
        "model": model,
        "stream": False,
        "messages": messages,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
            "top_p": 1.0,
            "repeat_penalty": 1.0,
        },
    }
    if json_mode:
        body["format"] = "json"

    last_exc: BaseException | None = None

    if _prefer_urllib:
        try:
            return await asyncio.to_thread(_chat_urllib, host, body)
        except Exception as exc:
            last_exc = exc
            logger.warning("urllib chat failed: %s", exc)

    try:
        url = f"{host}/api/chat"
        timeout = httpx.Timeout(600.0, connect=60.0)
        async with httpx_client(timeout=timeout) as client:
            r = await client.post(url, json=body)
            r.raise_for_status()
            data = r.json()
            return str(data.get("message", {}).get("content", ""))
    except Exception as exc:
        last_exc = exc
        logger.warning("httpx chat failed: %s", exc)

    try:
        text = await asyncio.to_thread(_chat_urllib, host, body)
        _prefer_urllib = True
        return text
    except Exception as exc:
        last_exc = exc
        raise ConnectionError(format_connection_help(last_exc)) from exc


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
        return False, f"Ollama at {host} has no models. Run: `ollama pull {requested}`"
    if not model_is_installed(requested, names):
        effective = pick_ollama_model(requested, names)
        return False, (
            f"Model `{requested}` not found. Installed: {', '.join(names)}. "
            f"Run `ollama pull {requested}` or set OLLAMA_MODEL={effective}"
        )
    effective = pick_ollama_model(requested, names)
    if effective != requested:
        return True, f"OK at {host} (model `{effective}`)"
    return True, f"OK at {host}"


async def warmup_ollama() -> tuple[bool, str]:
    try:
        host, names = await resolve_ollama(force=True)
        model = pick_ollama_model(get_settings().ollama_model, names)
        return True, f"Ready at {host} · model `{model}`"
    except Exception as exc:
        return False, format_connection_help(exc)
