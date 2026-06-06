"""Entity normalization via local Ollama (wraps local-llm)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from normalization.bridge import build_reference_from_names, normalize_team_labels


async def map_entities_to_canonical(
  fragments: Sequence[str],
  canonical_reference: Mapping[str, str],
  *,
  extra_hints: str | None = None,
) -> dict[str, str | None]:
  """
  Map messy labels (books, contracts, players) to canonical reference values.

  canonical_reference: slug -> display name (allowed outputs).
  """
  return await normalize_team_labels(fragments, canonical_reference, extra_hints=extra_hints)


def build_canonical_reference(*names: str) -> dict[str, str]:
  return build_reference_from_names(names)
