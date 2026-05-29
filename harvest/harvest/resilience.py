"""HTTP resilience: retries, jitter, rate-limit handling (compliant)."""

from __future__ import annotations

import random
import time
from typing import Callable, TypeVar

import httpx

T = TypeVar("T")

RETRYABLE_STATUS = {429, 500, 502, 503, 504}


def backoff_sleep(attempt: int, *, base: float = 0.5, cap: float = 60.0) -> None:
    delay = min(cap, base * (2**attempt))
    jitter = random.uniform(0, delay * 0.35)
    time.sleep(delay + jitter)


def request_json(
    client: httpx.Client,
    method: str,
    url: str,
    *,
    max_attempts: int = 5,
    **kwargs,
) -> dict:
    last_err: Exception | None = None
    for attempt in range(max_attempts):
        try:
            res = client.request(method, url, **kwargs)
            if res.status_code in RETRYABLE_STATUS:
                backoff_sleep(attempt)
                continue
            if res.status_code == 403:
                # Legitimate fix: credentials, IP allowlist, or reduce rate — not evasion
                res.raise_for_status()
            res.raise_for_status()
            return res.json()
        except (httpx.HTTPError, httpx.TimeoutException) as e:
            last_err = e
            if attempt + 1 >= max_attempts:
                raise
            backoff_sleep(attempt)
    raise RuntimeError("unreachable") from last_err


def run_with_retry(fn: Callable[[], T], *, max_attempts: int = 3) -> T:
    last: Exception | None = None
    for attempt in range(max_attempts):
        try:
            return fn()
        except Exception as e:
            last = e
            if attempt + 1 >= max_attempts:
                raise
            backoff_sleep(attempt)
    raise last  # type: ignore[misc]
