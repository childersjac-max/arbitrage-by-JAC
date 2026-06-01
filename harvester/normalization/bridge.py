"""Call local-llm normalize_batch from the harvester pipeline."""

from __future__ import annotations

import logging
import re
from collections.abc import Mapping, Sequence

from harvester_paths import LOCAL_LLM_DIR
from local_llm_bridge import import_local_llm, prepare_local_llm_path

logger = logging.getLogger(__name__)


def _slug(text: str) -> str:
    slug = re.sub(r"[^\w]+", "_", text.strip().lower())
    return slug.strip("_")[:80] or "entity"


def ensure_local_llm_importable() -> None:
    if not (LOCAL_LLM_DIR / "local_inference.py").is_file():
        raise RuntimeError(
            f"local-llm not found at {LOCAL_LLM_DIR}. "
            "Clone the repo branch that includes local-llm/."
        )
    prepare_local_llm_path()


def build_reference_from_names(names: Sequence[str]) -> dict[str, str]:
    """Map slug keys to canonical display names (initial pass: identity)."""
    ref: dict[str, str] = {}
    for name in names:
        clean = name.strip()
        if not clean:
            continue
        ref[_slug(clean)] = clean
    return ref


async def normalize_team_labels(
    fragments: Sequence[str],
    reference: Mapping[str, str] | None = None,
    *,
    extra_hints: str | None = None,
) -> dict[str, str | None]:
    """
    Normalize messy labels to canonical reference values via Ollama/vLLM.

    Returns mapping fragment -> canonical name or None.
    """
    ensure_local_llm_importable()
    local_inference = import_local_llm("local_inference")
    LocalInferenceClient = local_inference.LocalInferenceClient

    unique = sorted({f.strip() for f in fragments if f and f.strip()})
    if not unique:
        return {}

    ref = dict(reference) if reference else build_reference_from_names(unique)
    if not ref:
        ref = build_reference_from_names(unique)

    async with LocalInferenceClient() as client:
        result = await client.normalize_batch(unique, ref, extra_hints=extra_hints)
    return dict(result.mapping)
