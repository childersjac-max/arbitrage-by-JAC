#!/usr/bin/env python3
"""Example: normalize scraped sportsbook fragments via local Ollama/vLLM."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from local_inference import LocalInferenceClient

REFERENCE = {
    "nba_cha": "Charlotte Hornets",
    "nba_lal": "Los Angeles Lakers",
    "nba_bos": "Boston Celtics",
}

FRAGMENTS = [
    "CHA Hornets",
    "Charlotte",
    "Hornets -3.5",
    "Los Angeles L",
    "Lakers",
    "BOS Celtics",
]


async def main() -> None:
    async with LocalInferenceClient() as client:
        result = await client.normalize_batch(FRAGMENTS, REFERENCE)
        print(json.dumps(result.mapping, indent=2, ensure_ascii=False))
        print(f"attempts={result.attempts} latency_ms={result.latency_ms:.1f}")


if __name__ == "__main__":
    asyncio.run(main())
