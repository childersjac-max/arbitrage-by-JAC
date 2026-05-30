"""Bridge from harvester text fragments to the local-llm normalizer."""

from __future__ import annotations

import asyncio
import hashlib
import importlib.util
import inspect
import json
import sqlite3
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from harvester.config import HarvesterSettings
from harvester.normalize.reference_loader import ReferenceData, load_reference_data


class LocalLLMNormalizationBridge:
    """Batching, caching normalization bridge for raw event/team/market names."""

    def __init__(
        self,
        settings: HarvesterSettings,
        reference_data: ReferenceData | None = None,
        client: Any | None = None,
    ) -> None:
        self.settings = settings
        self.cache_path = settings.harvester_cache_path
        self.reference_data = reference_data or load_reference_data(settings.harvester_reference_path)
        self.client = client if client is not None else self._load_local_llm_client()
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_cache()

    async def normalize_batch(self, fragments: Iterable[str]) -> dict[str, str]:
        """Normalize raw strings using cache, aliases, and local LLM fallback."""

        ordered = [fragment.strip() for fragment in fragments if fragment and fragment.strip()]
        unique = list(dict.fromkeys(ordered))
        if not unique:
            return {}

        results: dict[str, str] = {}
        unresolved: list[str] = []
        for fragment in unique:
            cached = self._cache_get(fragment)
            if cached is not None:
                results[fragment] = cached
                continue
            ruled = self._rule_normalize(fragment)
            if ruled is not None:
                results[fragment] = ruled
                self._cache_set(fragment, ruled)
                continue
            unresolved.append(fragment)

        if unresolved and self.client is not None:
            for chunk in self._chunks(unresolved, self._batch_size()):
                try:
                    normalized = await self._call_client(chunk)
                except Exception:
                    normalized = {}
                for raw in chunk:
                    value = normalized.get(raw) or self._fallback_normalize(raw)
                    results[raw] = value
                    self._cache_set(raw, value)

        for raw in unresolved:
            if raw not in results:
                value = self._fallback_normalize(raw)
                results[raw] = value
                self._cache_set(raw, value)

        return {raw: results[raw] for raw in ordered if raw in results}

    def normalize_one_sync(self, fragment: str) -> str:
        """Synchronous convenience wrapper used by scripts and tests."""

        return asyncio.run(self.normalize_batch([fragment]))[fragment]

    def _batch_size(self) -> int:
        """Clamp LLM batch size to the requested 20-50 fragment range."""

        return min(50, max(20, int(self.settings.local_llm_batch_size)))

    async def _call_client(self, chunk: list[str]) -> dict[str, str]:
        """Call LocalInferenceClient.normalize_batch with temperature=0."""

        maybe_result = self.client.normalize_batch(chunk, temperature=0)
        if inspect.isawaitable(maybe_result):
            maybe_result = await maybe_result
        return self._coerce_client_result(chunk, maybe_result)

    def _coerce_client_result(self, chunk: list[str], value: Any) -> dict[str, str]:
        """Accept dict/list/string JSON outputs from local-llm clients."""

        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                return {}
        if isinstance(value, dict):
            if "normalized" in value and isinstance(value["normalized"], dict):
                value = value["normalized"]
            return {raw: str(value[raw]).strip() for raw in chunk if raw in value and str(value[raw]).strip()}
        if isinstance(value, list):
            mapped: dict[str, str] = {}
            for raw, item in zip(chunk, value, strict=False):
                if isinstance(item, dict):
                    normalized = item.get("normalized") or item.get("canonical") or item.get("value")
                else:
                    normalized = item
                if normalized:
                    mapped[raw] = str(normalized).strip()
            return mapped
        return {}

    def _rule_normalize(self, fragment: str) -> str | None:
        """Normalize by exact canonical lookup or alias table only."""

        return self.reference_data.lookup(fragment)

    def _fallback_normalize(self, fragment: str) -> str:
        """Safe deterministic fallback when Ollama is down."""

        return " ".join(fragment.strip().split())

    def _load_local_llm_client(self) -> Any | None:
        """Import LocalInferenceClient from the repository's local-llm package."""

        module_path = Path(__file__).resolve().parents[2] / "local-llm" / "local_inference.py"
        if not module_path.exists():
            return None
        spec = importlib.util.spec_from_file_location("local_llm_local_inference", module_path)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        module_dir = str(module_path.parent)
        if module_dir not in sys.path:
            sys.path.insert(0, module_dir)
        spec.loader.exec_module(module)
        client_cls = getattr(module, "LocalInferenceClient", None)
        if client_cls is None:
            return None
        return client_cls(
            base_url=self.settings.local_llm_base_url,
            model=self.settings.local_llm_model,
            timeout_seconds=self.settings.local_llm_timeout_seconds,
        )

    def _init_cache(self) -> None:
        """Create the sqlite cache table if needed."""

        with sqlite3.connect(self.cache_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS normalization_cache (
                    raw_hash TEXT PRIMARY KEY,
                    raw_text TEXT NOT NULL,
                    normalized_text TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.commit()

    def _cache_get(self, raw: str) -> str | None:
        """Return cached normalized text for a raw fragment."""

        with sqlite3.connect(self.cache_path) as conn:
            row = conn.execute(
                "SELECT normalized_text FROM normalization_cache WHERE raw_hash = ?",
                (self._hash(raw),),
            ).fetchone()
        return str(row[0]) if row else None

    def _cache_set(self, raw: str, normalized: str) -> None:
        """Persist a normalized fragment in the sqlite cache."""

        with sqlite3.connect(self.cache_path) as conn:
            conn.execute(
                """
                INSERT INTO normalization_cache(raw_hash, raw_text, normalized_text)
                VALUES (?, ?, ?)
                ON CONFLICT(raw_hash) DO UPDATE SET
                    raw_text = excluded.raw_text,
                    normalized_text = excluded.normalized_text
                """,
                (self._hash(raw), raw, normalized),
            )
            conn.commit()

    @staticmethod
    def _hash(raw: str) -> str:
        """Hash raw text for stable sqlite keys."""

        return hashlib.sha256(raw.casefold().strip().encode("utf-8")).hexdigest()

    @staticmethod
    def _chunks(values: list[str], size: int) -> Iterable[list[str]]:
        """Yield fixed-size chunks."""

        for index in range(0, len(values), size):
            yield values[index : index + size]
