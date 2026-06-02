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
from collections.abc import AsyncIterator
from typing import Any

import httpx

from config import get_settings
from paths import ENV_FILE

logger = logging.getLogger(__name__)

_resolved_host: str | None = None
_cached_models: list[str] | None = None
_prefer_urllib: bool = os.name == "nt"  # Windows: curl works; httpx often breaks via proxy


def prefer_buffered_transport() -> bool:
    """Use non-streaming Ollama HTTP (urllib) — reliable on Windows behind proxies."""
    return _prefer_urllib


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


def ollama_model_options(
    num_predict: int,
    *,
    temperature: float | None = None,
    num_ctx: int | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    temp = temperature if temperature is not None else settings.local_llm_prompt_temperature
    ctx = num_ctx if num_ctx is not None else settings.ollama_num_ctx
    return {
        "temperature": temp,
        "num_predict": num_predict,
        "top_p": settings.ollama_top_p,
        "repeat_penalty": settings.ollama_repeat_penalty,
        "num_ctx": ctx,
    }


def extract_ollama_chat_content(data: dict[str, Any]) -> str:
    """Parse Ollama /api/chat JSON (non-streaming)."""
    if err := data.get("error"):
        raise RuntimeError(f"Ollama error: {err}")
    msg = data.get("message") or {}
    content = str(msg.get("content", ""))
    if content.strip():
        return content
    if data.get("done"):
        reason = msg.get("done_reason") or data.get("done_reason") or "unknown"
        raise RuntimeError(
            "Ollama returned an empty reply "
            f"(done_reason={reason}). "
            "Try lowering max tokens, shortening the system prompt, or run `ollama logs`."
        )
    return content


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
    return extract_ollama_chat_content(data)


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


def _ollama_chat_body(
    messages: list[dict[str, str]],
    *,
    model: str,
    temperature: float,
    max_tokens: int,
    stream: bool,
    json_mode: bool = False,
    for_chat_ui: bool = False,
) -> dict[str, Any]:
    settings = get_settings()
    ctx = settings.ollama_chat_num_ctx if for_chat_ui else None
    body: dict[str, Any] = {
        "model": model,
        "stream": stream,
        "messages": messages,
        "keep_alive": "10m",
        "options": ollama_model_options(
            max_tokens,
            temperature=temperature,
            num_ctx=ctx,
        ),
    }
    if json_mode:
        body["format"] = "json"
    return body


async def ollama_chat_stream(
    messages: list[dict[str, str]],
    *,
    model: str,
    temperature: float,
    max_tokens: int,
) -> AsyncIterator[str]:
    """
    Stream tokens from Ollama /api/chat (httpx, trust_env=False for localhost).
    """
    host = get_ollama_base_url()
    await resolve_ollama()
    body = _ollama_chat_body(
        messages,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=True,
        for_chat_ui=True,
    )
    url = f"{host}/api/chat"
    timeout = httpx.Timeout(None, connect=60.0)
    async with httpx_client(timeout=timeout) as client:
        async with client.stream("POST", url, json=body) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line:
                    continue
                try:
                    chunk = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if chunk.get("error"):
                    raise RuntimeError(f"Ollama error: {chunk['error']}")
                token = chunk.get("message", {}).get("content", "")
                if token:
                    yield str(token)
                if chunk.get("done"):
                    return


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

    body = _ollama_chat_body(
        messages,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=False,
        json_mode=json_mode,
    )

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
            return extract_ollama_chat_content(r.json())
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
    effective = pick_ollama_model(requested, names)
    if not model_is_installed(requested, names):
        return True, (
            f"OK at {host} — will use `{effective}` "
            f"(configured `{requested}` is not installed). "
            f"Installed: {', '.join(names)}. "
            f"To match .env exactly: `ollama pull {requested}` "
            f"or set OLLAMA_MODEL={effective} in `local-llm/.env`."
        )
    if effective != requested:
        return True, f"OK at {host} (using model `{effective}`)"
    return True, f"OK at {host} · model `{effective}`"


async def warmup_ollama() -> tuple[bool, str]:
    try:
        host, names = await resolve_ollama(force=True)
        model = pick_ollama_model(get_settings().ollama_model, names)
        return True, f"Ready at {host} · model `{model}`"
    except Exception as exc:
        return False, format_connection_help(exc)
