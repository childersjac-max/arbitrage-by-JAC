"""Resilient HTTP client with polite retries — for authorized public APIs only."""

from __future__ import annotations

import random
import time
from typing import Any

from ..config import CollectorConfig

try:
    from curl_cffi import requests as cffi_requests

    HAS_CURL_CFFI = True
except ImportError:
    HAS_CURL_CFFI = False

import httpx


class ResilientHttpClient:
    """
    HTTP layer prioritizing stable access to documented APIs.

    Uses curl_cffi with a Chrome impersonation profile when available so
    requests resemble a standard desktop browser — useful for APIs that
    reject generic Python user-agents, not for circumventing access controls.
    """

    DEFAULT_HEADERS = {
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache",
    }

    def __init__(self, config: CollectorConfig):
        self.config = config
        self._httpx = httpx.Client(
            timeout=config.request_timeout_sec,
            headers=self.DEFAULT_HEADERS,
            proxy=config.proxy_url,
            follow_redirects=True,
        )

    def close(self) -> None:
        self._httpx.close()

    def _backoff(self, attempt: int, status: int | None = None) -> float:
        base = min(2**attempt, 32)
        jitter = random.uniform(0.4, 1.6)
        if status == 429:
            base *= 2
        return base * jitter

    def get_json(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        min_interval_sec: float = 0.0,
        last_request_at: list[float] | None = None,
    ) -> dict[str, Any] | list[Any] | None:
        """GET with retries on 429/5xx; returns parsed JSON or None."""
        if last_request_at is not None and min_interval_sec > 0:
            elapsed = time.monotonic() - last_request_at[0]
            if elapsed < min_interval_sec:
                time.sleep(min_interval_sec - elapsed)

        merged_headers = {**self.DEFAULT_HEADERS, **(headers or {})}
        last_status: int | None = None

        for attempt in range(self.config.max_retries + 1):
            try:
                if self.config.use_curl_cffi and HAS_CURL_CFFI:
                    resp = cffi_requests.get(
                        url,
                        params=params,
                        headers=merged_headers,
                        timeout=self.config.request_timeout_sec,
                        impersonate="chrome131",
                        proxies=(
                            {"http": self.config.proxy_url, "https": self.config.proxy_url}
                            if self.config.proxy_url
                            else None
                        ),
                    )
                    status = resp.status_code
                    text = resp.text
                else:
                    resp = self._httpx.get(url, params=params, headers=merged_headers)
                    status = resp.status_code
                    text = resp.text

                last_status = status
                if last_request_at is not None:
                    last_request_at[0] = time.monotonic()

                if status == 200:
                    import json

                    return json.loads(text)

                if status in (403, 429) or status >= 500:
                    if attempt < self.config.max_retries:
                        time.sleep(self._backoff(attempt, status))
                        continue
                    return None

                return None
            except Exception:
                if attempt < self.config.max_retries:
                    time.sleep(self._backoff(attempt, last_status))
                    continue
                return None
        return None
