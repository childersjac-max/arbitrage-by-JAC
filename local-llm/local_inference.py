"""Local Ollama inference client used only for fuzzy normalization."""

from __future__ import annotations

import json
from typing import Any

import httpx

try:
    from normalization_prompt import build_normalization_prompt
except ImportError:  # pragma: no cover - supports package-style imports.
    from .normalization_prompt import build_normalization_prompt


class LocalInferenceError(RuntimeError):
    """Raised when local inference is unavailable or returns invalid output."""


class LocalInferenceClient:
    """Minimal Ollama client for deterministic normalization batches."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3.1",
        timeout_seconds: float = 20.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    async def normalize_batch(self, fragments: list[str], temperature: float = 0) -> dict[str, str]:
        """Normalize raw strings with Ollama and return raw-to-canonical mapping."""

        if not fragments:
            return {}
        prompt = build_normalization_prompt(fragments)
        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": temperature},
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(f"{self.base_url}/api/generate", json=payload)
        except httpx.HTTPError as exc:
            raise LocalInferenceError(f"Ollama request failed: {exc}") from exc
        if response.status_code >= 400:
            raise LocalInferenceError(f"Ollama HTTP {response.status_code}: {response.text[:250]}")
        body = response.json()
        raw_response = body.get("response")
        if not isinstance(raw_response, str):
            raise LocalInferenceError("Ollama response did not include text output")
        try:
            parsed = json.loads(raw_response)
        except json.JSONDecodeError as exc:
            raise LocalInferenceError("Ollama returned invalid JSON") from exc
        normalized = parsed.get("normalized", parsed)
        if not isinstance(normalized, dict):
            raise LocalInferenceError("Ollama normalization output was not a mapping")
        return {
            raw: str(normalized.get(raw, raw)).strip() or raw
            for raw in fragments
        }
