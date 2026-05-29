"""
Async local LLM client for high-throughput entity normalization.

Supports:
  - Ollama native API (POST /api/chat)
  - vLLM / OpenAI-compatible (POST /v1/chat/completions)

Features: connection pooling, batched concurrent requests, strict JSON retry loop.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

import httpx

from config import Backend, LocalLLMSettings, get_settings
from normalization_prompt import (
    SYSTEM_PROMPT,
    build_retry_user_message,
    build_user_message,
    extract_json_object,
    validate_mapping,
)

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

    Example:
        async with LocalInferenceClient() as client:
            result = await client.normalize_batch(
                ["CHA Hornets", "Charlotte"],
                reference={"nba_cha": "Charlotte Hornets"},
            )
    """

    settings: LocalLLMSettings = field(default_factory=get_settings)
    _client: httpx.AsyncClient | None = field(default=None, repr=False)
    _semaphore: asyncio.Semaphore | None = field(default=None, repr=False)

    async def __aenter__(self) -> LocalInferenceClient:
        await self.start()
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()

    async def start(self) -> None:
        if self._client is not None:
            return
        limits = httpx.Limits(
            max_connections=self.settings.local_llm_max_connections,
            max_keepalive_connections=self.settings.local_llm_max_connections,
        )
        timeout = httpx.Timeout(self.settings.local_llm_timeout_sec)
        self._client = httpx.AsyncClient(limits=limits, timeout=timeout)
        self._semaphore = asyncio.Semaphore(self.settings.local_llm_batch_concurrency)

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("Client not started; use 'async with LocalInferenceClient()'")
        return self._client

    async def health_check(self) -> dict[str, Any]:
        """Quick reachability check for the configured backend."""
        client = self._ensure_client()
        backend = self.settings.local_llm_backend
        if backend == Backend.OLLAMA:
            url = f"{self.settings.resolved_base_url()}/api/tags"
            r = await client.get(url)
            r.raise_for_status()
            return {"backend": "ollama", "status": "ok", "tags": r.json()}
        url = f"{self.settings.resolved_base_url()}/models"
        r = await client.get(url)
        r.raise_for_status()
        return {"backend": str(backend), "status": "ok", "models": r.json()}

    async def _chat_completion(self, user_content: str) -> str:
        client = self._ensure_client()
        backend = self.settings.local_llm_backend
        temperature = self.settings.local_llm_temperature
        max_tokens = self.settings.local_llm_max_tokens
        model = self.settings.resolved_model()

        if backend == Backend.OLLAMA:
            url = f"{self.settings.resolved_base_url()}/api/chat"
            body = {
                "model": model,
                "stream": False,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                    "top_p": 1.0,
                    "repeat_penalty": 1.0,
                },
                "format": "json",
            }
            response = await client.post(url, json=body)
            response.raise_for_status()
            data = response.json()
            return str(data.get("message", {}).get("content", ""))

        # vLLM / OpenAI-compatible
        url = f"{self.settings.resolved_base_url()}/chat/completions"
        body = {
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            "response_format": {"type": "json_object"},
        }
        response = await client.post(url, json=body)
        response.raise_for_status()
        data = response.json()
        choices = data.get("choices") or []
        if not choices:
            return ""
        return str(choices[0].get("message", {}).get("content", ""))

    async def normalize_batch(
        self,
        fragments: Sequence[str],
        reference: Mapping[str, str],
        *,
        extra_hints: str | None = None,
    ) -> InferenceResult:
        """
        Normalize a batch of raw strings to canonical reference values.

        Retries on timeout, HTTP errors, invalid JSON, or schema validation failure.
        """
        if self._semaphore is None:
            await self.start()
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
                raw = await self._chat_completion(user_msg)
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
            except httpx.TimeoutException as exc:
                last_error = f"timeout: {exc}"
                logger.warning("normalize_batch attempt %s timeout", attempt)
            except httpx.HTTPError as exc:
                last_error = f"http: {exc}"
                logger.warning("normalize_batch attempt %s http error: %s", attempt, exc)
            except (ValueError, json.JSONDecodeError) as exc:
                if not isinstance(exc, json.JSONDecodeError):
                    last_error = str(exc)
                else:
                    last_error = f"json: {exc}"
                logger.warning("normalize_batch attempt %s parse error: %s", attempt, exc)
            except Exception as exc:
                last_error = f"unexpected: {exc}"
                logger.exception("normalize_batch attempt %s failed", attempt)

            if attempt < max_retries:
                await asyncio.sleep(min(0.25 * (2 ** (attempt - 1)), 2.0))

        latency_ms = (time.perf_counter() - t0) * 1000
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
