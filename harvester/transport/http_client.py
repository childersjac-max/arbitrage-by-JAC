"""
Async HTTP/2 client for lawful API access.

Uses httpx with connection pooling, structured retries on 429/5xx, and
optional proxy URL from configuration. Does NOT modify TLS fingerprints or
spoof browser environments — use only against endpoints you are authorized to call.
"""

from __future__ import annotations

import asyncio
import logging
import random
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class TransportError(Exception):
  def __init__(self, message: str, *, status: int | None = None) -> None:
    super().__init__(message)
    self.status = status


@dataclass
class HttpTransport:
  """
  Pooled async HTTP client.

  proxy_url: optional HTTP(S) proxy from your network provider (authorized use only).
  """

  base_url: str = ""
  timeout_sec: float = 30.0
  max_retries: int = 4
  max_connections: int = 32
  user_agent: str = "harvester/1.0 (+lawful-api-client)"
  proxy_url: str | None = None
  _client: httpx.AsyncClient | None = field(default=None, repr=False)

  async def __aenter__(self) -> HttpTransport:
    await self.start()
    return self

  async def __aexit__(self, *args: object) -> None:
    await self.close()

  async def start(self) -> None:
    if self._client is not None:
      return
    limits = httpx.Limits(
      max_connections=self.max_connections,
      max_keepalive_connections=self.max_connections,
    )
    timeout = httpx.Timeout(self.timeout_sec)
    kwargs: dict[str, Any] = {
      "limits": limits,
      "timeout": timeout,
      "headers": {"User-Agent": self.user_agent, "Accept": "application/json"},
      "trust_env": False,
      "http2": True,
    }
    if self.proxy_url:
      kwargs["proxy"] = self.proxy_url
    base = self.base_url.rstrip("/") if self.base_url else None
    self._client = httpx.AsyncClient(base_url=base, **kwargs)

  async def close(self) -> None:
    if self._client is not None:
      await self._client.aclose()
      self._client = None

  def _client_required(self) -> httpx.AsyncClient:
    if self._client is None:
      raise RuntimeError("HttpTransport not started; use async with HttpTransport()")
    return self._client

  async def _backoff(self, attempt: int) -> None:
    base = min(60.0, 2.0 ** attempt)
    jitter = random.uniform(0.0, base * 0.25)
    await asyncio.sleep(base + jitter)

  async def request(
    self,
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
  ) -> Any:
    client = self._client_required()
    last_exc: Exception | None = None

    for attempt in range(self.max_retries + 1):
      try:
        resp = await client.request(method, path, params=params, json=json_body)
        if resp.status_code == 429:
          logger.warning("429 rate limited (attempt %s)", attempt + 1)
          if attempt < self.max_retries:
            await self._backoff(attempt)
            continue
          raise TransportError("Rate limited (429)", status=429)
        if resp.status_code == 403:
          raise TransportError(
            "Forbidden (403) — endpoint may block automated access; use official API credentials",
            status=403,
          )
        if resp.status_code >= 500:
          logger.warning("Server %s (attempt %s)", resp.status_code, attempt + 1)
          if attempt < self.max_retries:
            await self._backoff(attempt)
            continue
        resp.raise_for_status()
        return resp.json()
      except TransportError:
        raise
      except httpx.HTTPStatusError as exc:
        last_exc = exc
        if attempt < self.max_retries and exc.response.status_code >= 500:
          await self._backoff(attempt)
          continue
        raise TransportError(str(exc), status=exc.response.status_code) from exc
      except Exception as exc:
        last_exc = exc
        if attempt < self.max_retries:
          await self._backoff(attempt)
          continue
        raise TransportError(str(exc)) from exc

    raise TransportError(str(last_exc or "request failed"))
