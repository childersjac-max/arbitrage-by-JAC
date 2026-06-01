"""
Async local LLM client: entity normalization + free-form prompting.

Supports:
  - Ollama native API (POST /api/chat)
  - vLLM / OpenAI-compatible (POST /v1/chat/completions)
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

import httpx

from config import Backend, LocalLLMSettings, get_settings
from ollama_connect import (
    get_effective_ollama_model,
    get_ollama_base_url,
    httpx_client,
    ollama_chat_completion,
    ollama_model_options,
    prefer_buffered_transport,
    resolve_ollama,
)
from prompt_loader import get_default_system_prompt
from normalization_prompt import (
    SYSTEM_PROMPT,
    build_retry_user_message,
    build_user_message,
    extract_json_object,
    validate_mapping,
)
from prompt_types import ChatMessage, PromptResult

logger = logging.getLogger(__name__)


@dataclass
class InferenceResult:
    mapping: dict[str, str | None]
    raw_response: str
    attempts: int
    latency_ms: float


@dataclass
class LocalInferenceClient:
    """
    Pooled async HTTP client for localhost inference.

    Normalization (fixed JSON prompt):
        await client.normalize_batch(fragments, reference)

    Free-form prompting:
        await client.complete("Explain asyncio in Python")
        await client.chat([ChatMessage("user", "Hi"), ...])
    """

    settings: LocalLLMSettings = field(default_factory=get_settings)
    _client: httpx.AsyncClient | None = field(default=None, repr=False)
    _semaphore: asyncio.Semaphore | None = field(default=None, repr=False)
    _read_timeout_sec: float | None = field(default=None, repr=False)

    async def __aenter__(self) -> LocalInferenceClient:
        await self.start(prompt_mode=True)
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()

    async def start(self, *, prompt_mode: bool = False) -> None:
        read_seconds = (
            self.settings.local_llm_prompt_timeout_sec
            if prompt_mode
            else self.settings.local_llm_timeout_sec
        )
        if self._client is not None and self._read_timeout_sec == read_seconds:
            return
        if self._client is not None:
            await self.close()

        limits = httpx.Limits(
            max_connections=self.settings.local_llm_max_connections,
            max_keepalive_connections=self.settings.local_llm_max_connections,
        )
        # Explicit read timeout: Ollama can take minutes on first load (esp. CPU/Windows).
        timeout = httpx.Timeout(
            connect=30.0,
            read=read_seconds,
            write=120.0,
            pool=30.0,
        )
        self._read_timeout_sec = read_seconds
        self._client = httpx_client(limits=limits, timeout=timeout)
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.settings.local_llm_batch_concurrency)

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
        self._read_timeout_sec = None

    def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("Client not started; use 'async with LocalInferenceClient()'")
        return self._client

    async def health_check(self) -> dict[str, Any]:
        """Quick reachability check for the configured backend."""
        client = self._ensure_client()
        backend = self.settings.local_llm_backend
        if backend == Backend.OLLAMA:
            host, names = await resolve_ollama()
            model = await get_effective_ollama_model()
            return {
                "backend": "ollama",
                "status": "ok",
                "host": host,
                "model": model,
                "installed_models": names,
            }
        url = f"{self.settings.resolved_base_url()}/models"
        r = await client.get(url)
        r.raise_for_status()
        return {"backend": str(backend), "status": "ok", "models": r.json()}

    def _build_messages(
        self,
        prompt: str,
        *,
        system: str | None = None,
        history: Sequence[ChatMessage] | None = None,
    ) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []
        sys_content = system if system is not None else get_default_system_prompt()
        if sys_content:
            messages.append({"role": "system", "content": sys_content})
        if history:
            messages.extend(m.to_api_dict() for m in history)
        messages.append({"role": "user", "content": prompt})
        return messages

    async def _invoke_messages(
        self,
        messages: list[dict[str, str]],
        *,
        json_mode: bool = False,
        temperature: float | None = None,
        max_tokens: int | None = None,
        stream: bool = False,
        on_token: Callable[[str], None] | None = None,
    ) -> str:
        client = self._ensure_client()
        backend = self.settings.local_llm_backend
        model = self.settings.resolved_model()
        if backend == Backend.OLLAMA:
            await resolve_ollama()
            try:
                model = await get_effective_ollama_model()
            except Exception:
                model = self.settings.ollama_model
        temp = (
            temperature
            if temperature is not None
            else (
                self.settings.local_llm_temperature
                if json_mode
                else self.settings.local_llm_prompt_temperature
            )
        )
        tokens = (
            max_tokens
            if max_tokens is not None
            else (
                self.settings.local_llm_max_tokens
                if json_mode
                else self.settings.local_llm_prompt_max_tokens
            )
        )

        if backend == Backend.OLLAMA:
            if not stream or prefer_buffered_transport():
                text = await ollama_chat_completion(
                    messages,
                    model=model,
                    temperature=temp,
                    max_tokens=tokens,
                    json_mode=json_mode,
                )
                if stream and on_token and text:
                    on_token(text)
                return text

            base = get_ollama_base_url()
            url = f"{base}/api/chat"
            body = {
                "model": model,
                "stream": True,
                "messages": messages,
                "options": ollama_model_options(tokens, temperature=temp),
            }
            if json_mode:
                body["format"] = "json"
            full: list[str] = []
            async with client.stream("POST", url, json=body) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    token = chunk.get("message", {}).get("content", "")
                    if token:
                        full.append(token)
                        if on_token:
                            on_token(token)
                    if chunk.get("done"):
                        break
            return "".join(full)

        url = f"{self.settings.resolved_base_url()}/chat/completions"
        body = {
            "model": model,
            "temperature": temp,
            "max_tokens": tokens,
            "messages": messages,
            "stream": stream,
        }
        if json_mode:
            body["response_format"] = {"type": "json_object"}

        if not stream:
            response = await client.post(url, json=body)
            response.raise_for_status()
            data = response.json()
            choices = data.get("choices") or []
            if not choices:
                return ""
            return str(choices[0].get("message", {}).get("content", ""))

        full = []
        async with client.stream("POST", url, json=body) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith("data:"):
                    continue
                payload = line[5:].strip()
                if payload == "[DONE]":
                    break
                try:
                    chunk = json.loads(payload)
                except json.JSONDecodeError:
                    continue
                delta = chunk.get("choices", [{}])[0].get("delta", {})
                token = delta.get("content", "")
                if token:
                    full.append(token)
                    if on_token:
                        on_token(token)
        return "".join(full)

    async def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        history: Sequence[ChatMessage] | None = None,
        json_mode: bool = False,
        temperature: float | None = None,
        max_tokens: int | None = None,
        stream: bool = False,
        on_token: Callable[[str], None] | None = None,
    ) -> PromptResult:
        """
        Send a free-form user prompt and return the model's text response.

        Does not use the normalization system prompt unless you pass system=SYSTEM_PROMPT.
        """
        await self.start(prompt_mode=True)
        messages = self._build_messages(prompt, system=system, history=history)
        t0 = time.perf_counter()
        content = await self._invoke_messages(
            messages,
            json_mode=json_mode,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream,
            on_token=on_token,
        )
        return PromptResult(
            content=content,
            model=self.settings.resolved_model(),
            latency_ms=(time.perf_counter() - t0) * 1000,
            backend=str(self.settings.local_llm_backend.value),
        )

    async def chat(
        self,
        messages: Sequence[ChatMessage],
        *,
        json_mode: bool = False,
        temperature: float | None = None,
        max_tokens: int | None = None,
        stream: bool = False,
        on_token: Callable[[str], None] | None = None,
    ) -> PromptResult:
        """Multi-turn chat: pass full message list (system/user/assistant)."""
        await self.start(prompt_mode=True)
        api_messages = [m.to_api_dict() for m in messages]
        if not api_messages or api_messages[-1]["role"] == "assistant":
            raise ValueError("chat() requires messages ending with a user message")
        t0 = time.perf_counter()
        content = await self._invoke_messages(
            api_messages,
            json_mode=json_mode,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream,
            on_token=on_token,
        )
        return PromptResult(
            content=content,
            model=self.settings.resolved_model(),
            latency_ms=(time.perf_counter() - t0) * 1000,
            backend=str(self.settings.local_llm_backend.value),
        )

    async def _chat_completion_normalize(self, user_content: str) -> str:
        """Normalization path: fixed system prompt + JSON output."""
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]
        return await self._invoke_messages(
            messages,
            json_mode=True,
            temperature=self.settings.local_llm_temperature,
            max_tokens=self.settings.local_llm_max_tokens,
        )

    async def normalize_batch(
        self,
        fragments: Sequence[str],
        reference: Mapping[str, str],
        *,
        extra_hints: str | None = None,
    ) -> InferenceResult:
        """Normalize raw strings to canonical reference values (JSON mapping)."""
        await self.start(prompt_mode=False)
        assert self._semaphore is not None

        async with self._semaphore:
            return await self._normalize_with_retries(fragments, reference, extra_hints=extra_hints)

    async def _normalize_with_retries(
        self,
        fragments: Sequence[str],
        reference: Mapping[str, str],
        *,
        extra_hints: str | None = None,
    ) -> InferenceResult:
        max_retries = self.settings.local_llm_max_retries
        user_msg = build_user_message(fragments, reference, extra_hints=extra_hints)
        last_output = ""
        last_error = ""
        t0 = time.perf_counter()

        for attempt in range(1, max_retries + 1):
            try:
                if attempt > 1 and last_output:
                    user_msg = build_retry_user_message(
                        fragments, reference, last_output, last_error
                    )
                raw = await self._chat_completion_normalize(user_msg)
                last_output = raw
                parsed = extract_json_object(raw)
                validated = validate_mapping(parsed, fragments, reference)
                latency_ms = (time.perf_counter() - t0) * 1000
                return InferenceResult(
                    mapping=validated,
                    raw_response=raw,
                    attempts=attempt,
                    latency_ms=latency_ms,
                )
            except ConnectionError as exc:
                last_error = str(exc)
                logger.warning("normalize_batch attempt %s connection error", attempt)
                break
            except httpx.TimeoutException as exc:
                last_error = f"timeout: {exc}"
                logger.warning("normalize_batch attempt %s timeout", attempt)
            except httpx.HTTPError as exc:
                last_error = f"http: {exc}"
                logger.warning("normalize_batch attempt %s http error: %s", attempt, exc)
            except (ValueError, json.JSONDecodeError) as exc:
                last_error = str(exc) if not isinstance(exc, json.JSONDecodeError) else f"json: {exc}"
                logger.warning("normalize_batch attempt %s parse error: %s", attempt, exc)
            except Exception as exc:
                last_error = f"unexpected: {exc}"
                logger.exception("normalize_batch attempt %s failed", attempt)

            if attempt < max_retries:
                await asyncio.sleep(min(0.25 * (2 ** (attempt - 1)), 2.0))

        raise RuntimeError(
            f"normalize_batch failed after {max_retries} attempts: {last_error}; "
            f"last_output={last_output[:500]!r}"
        )

    async def normalize_many_batches(
        self,
        batches: Sequence[tuple[Sequence[str], Mapping[str, str]]],
    ) -> list[InferenceResult]:
        """Run multiple normalization batches concurrently (bounded by semaphore)."""
        tasks = [self.normalize_batch(frags, ref) for frags, ref in batches]
        return list(await asyncio.gather(*tasks))
