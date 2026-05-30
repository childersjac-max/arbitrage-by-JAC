"""Load canonical entity references and aliases from JSON or YAML."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ReferenceData:
    """Canonical names and aliases used before falling back to local LLM."""

    def __init__(self, canonical: set[str] | None = None, aliases: dict[str, str] | None = None) -> None:
        self.canonical = canonical or set()
        self.aliases = {self._key(k): v for k, v in (aliases or {}).items()}

    def lookup(self, raw: str) -> str | None:
        """Return a canonical match from exact name or alias table."""

        key = self._key(raw)
        for canonical in self.canonical:
            if self._key(canonical) == key:
                return canonical
        return self.aliases.get(key)

    @staticmethod
    def _key(value: str) -> str:
        return " ".join(value.casefold().strip().split())


def load_reference_data(path: Path | None) -> ReferenceData:
    """Load reference data from JSON/YAML.

    Expected shape:
    {
      "canonical": ["Boston Celtics"],
      "aliases": {"BOS Celtics": "Boston Celtics"}
    }
    """

    if path is None or not path.exists():
        return ReferenceData()

    data = _read_structured(path)
    canonical = set(_string_list(data.get("canonical", [])))
    aliases = {
        str(raw): str(canonical_name)
        for raw, canonical_name in dict(data.get("aliases", {})).items()
        if raw and canonical_name
    }
    return ReferenceData(canonical=canonical, aliases=aliases)


def _read_structured(path: Path) -> dict[str, Any]:
    """Read JSON or YAML without requiring PyYAML unless YAML is used."""

    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        payload = json.loads(text)
    else:
        try:
            import yaml  # type: ignore[import-untyped]
        except ImportError as exc:
            raise RuntimeError("YAML reference files require installing PyYAML") from exc
        payload = yaml.safe_load(text)
    return payload if isinstance(payload, dict) else {}


def _string_list(value: Any) -> list[str]:
    """Return only string entries from an arbitrary list-like object."""

    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item.strip()]
