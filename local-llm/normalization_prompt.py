"""
Hardcoded prompt templates for sportsbook / prediction-market entity normalization.

The model must return ONLY a minified JSON object mapping each raw fragment to a
canonical key from the reference dictionary (or null if no match).
"""

from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

# Compact system prompt — no policy disclaimers; optimized for token efficiency.
SYSTEM_PROMPT = """You are a deterministic entity-resolution engine for sports betting data.
Given a reference map of official canonical names and a list of raw scraped text fragments,
output ONLY a single minified JSON object with no markdown, no prose, and no code fences.

Rules:
1. Keys in the output MUST be the exact raw input strings (byte-for-byte).
2. Values MUST be either a string from the reference values (exact match) or null if unmappable.
3. Prefer the closest fuzzy match (abbreviations, city-only, nicknames, typos) to one reference value.
4. Never invent canonical names not present in the reference.
5. If multiple fragments map to the same entity, use the same canonical string value.

Output schema: {"<raw_fragment>":"<canonical_or_null>", ...}"""


def build_reference_block(reference: Mapping[str, str]) -> str:
    """Serialize official names for the prompt (canonical -> aliases optional)."""
    # Flatten to sorted unique canonical values for the model to choose from.
    canonicals = sorted({v.strip() for v in reference.values() if v and v.strip()})
    return json.dumps(canonicals, separators=(",", ":"), ensure_ascii=False)


def build_user_message(
    fragments: Sequence[str],
    reference: Mapping[str, str],
    *,
    extra_hints: str | None = None,
) -> str:
    """
    Build the user payload: reference list + batch of raw strings.

    ``reference`` is typically id -> canonical name, e.g.
    {"cha": "Charlotte Hornets", "hornets": "Charlotte Hornets"}.
    """
    unique_fragments = list(dict.fromkeys(fragments))
    payload: dict[str, Any] = {
        "reference_canonical_names": json.loads(build_reference_block(reference)),
        "raw_fragments": unique_fragments,
    }
    if extra_hints:
        payload["hints"] = extra_hints
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)


def build_retry_user_message(
    fragments: Sequence[str],
    reference: Mapping[str, str],
    previous_output: str,
    error: str,
) -> str:
    """Stricter reformatted prompt after invalid JSON or schema failure."""
    base = build_user_message(fragments, reference)
    repair = {
        "error": error[:500],
        "invalid_previous_output": previous_output[:2000],
        "instruction": (
            "Your last response was invalid. Return ONLY valid minified JSON. "
            "Keys must equal each raw_fragment exactly. Values must be from "
            "reference_canonical_names or null."
        ),
    }
    return base + "\nREPAIR:\n" + json.dumps(repair, separators=(",", ":"))


def extract_json_object(text: str) -> dict[str, str | None]:
    """
    Parse model output into a dict. Strips markdown fences if the model disobeys once.
    """
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.split("\n")
        inner: list[str] = []
        for line in lines[1:]:
            if line.strip().startswith("```"):
                break
            inner.append(line)
        stripped = "\n".join(inner).strip()

    # Find outermost JSON object
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in model output")

    parsed = json.loads(stripped[start : end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("Expected JSON object")

    result: dict[str, str | None] = {}
    for key, value in parsed.items():
        if value is None:
            result[str(key)] = None
        elif isinstance(value, str):
            result[str(key)] = value
        else:
            result[str(key)] = str(value)
    return result


def validate_mapping(
    mapping: dict[str, str | None],
    fragments: Sequence[str],
    reference: Mapping[str, str],
) -> dict[str, str | None]:
    """Ensure keys cover fragments and values are allowed canonicals or null."""
    allowed = {v.strip() for v in reference.values() if v and v.strip()}
    expected_keys = set(fragments)
    out: dict[str, str | None] = {}

    for frag in expected_keys:
        if frag not in mapping:
            raise ValueError(f"Missing key for fragment: {frag!r}")
        val = mapping[frag]
        if val is not None and val not in allowed:
            raise ValueError(f"Value not in reference: {val!r}")
        out[frag] = val

    # Ignore extra keys from the model
    return out
