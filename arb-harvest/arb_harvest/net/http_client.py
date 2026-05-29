"""HTTP client with polite rate limiting and retry on transient errors."""

from __future__ import annotations

import random
import threading
import time
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class PoliteHttpClient:
    """Thread-safe client that respects per-host RPS and Retry-After headers."""

    def __init__(self, requests_per_second: float = 2.0, timeout: float = 20.0):
        self._min_interval = 1.0 / max(requests_per_second, 0.1)
        self._timeout = timeout
        self._lock = threading.Lock()
        self._last_request_at = 0.0
        self._session = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=(408, 429, 500, 502, 503, 504),
            allowed_methods=frozenset(["GET", "HEAD"]),
            respect_retry_after_header=True,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self._session.mount("https://", adapter)
        self._session.mount("http://", adapter)
        self._session.headers.update(
            {
                "Accept": "application/json",
                "User-Agent": "arb-harvest/0.1 (+https://github.com; compliance polling)",
            }
        )

    def _throttle(self) -> None:
        with self._lock:
            now = time.monotonic()
            wait = self._min_interval - (now - self._last_request_at)
            if wait > 0:
                time.sleep(wait)
            self._last_request_at = time.monotonic()

    def get_json(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any | None:
        self._throttle()
        try:
            resp = self._session.get(
                url,
                params=params,
                headers=headers,
                timeout=self._timeout,
            )
            if resp.status_code == 429:
                retry_after = resp.headers.get("Retry-After")
                sleep_s = float(retry_after) if retry_after else 5.0
                sleep_s += random.uniform(0.2, 1.0)
                time.sleep(sleep_s)
                return self.get_json(url, params=params, headers=headers)
            if resp.status_code >= 400:
                return None
            return resp.json()
        except requests.RequestException:
            return None
