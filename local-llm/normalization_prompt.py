"""Prompts for local entity normalization."""

from __future__ import annotations


NORMALIZATION_SYSTEM_PROMPT = """You normalize sports and prediction-market entities.
Return only JSON that maps each raw input string to a concise canonical name.
Do not invent events, odds, sources, URLs, or market data."""


def build_normalization_prompt(fragments: list[str]) -> str:
    """Build a deterministic prompt for a batch of raw fragments."""

    numbered = "\n".join(f"- {fragment}" for fragment in fragments)
    return (
        f"{NORMALIZATION_SYSTEM_PROMPT}\n\n"
        "Normalize these strings. Preserve meaning and use common team/event names:\n"
        f"{numbered}\n\n"
        "Return JSON in this exact shape: {\"normalized\": {\"raw\": \"canonical\"}}"
    )
