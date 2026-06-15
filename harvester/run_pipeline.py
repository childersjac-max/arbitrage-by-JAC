#!/usr/bin/env python3
"""CLI: lawful multi-adapter ingest → align → JSON stream."""

from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path

from adapters.registry import AdapterRegistry
from pipeline.align import align_events
from pipeline.stream import stream_json_lines
from settings import get_settings


async def main_async(args: argparse.Namespace) -> int:
  sport = args.sport or get_settings().default_sport_key
  registry = AdapterRegistry()
  events = await registry.gather_events(sport)

  if args.align:
    events = await align_events(events, use_ollama=True)

  text = stream_json_lines(events)
  out = Path(args.output)
  out.parent.mkdir(parents=True, exist_ok=True)
  out.write_text(text + ("\n" if text else ""), encoding="utf-8")
  print(f"events={len(events)} lines_written={text.count(chr(10)) + (1 if text else 0)} path={out}")
  return 0


def main() -> None:
  logging.basicConfig(level=logging.INFO)
  p = argparse.ArgumentParser()
  p.add_argument("--sport", default=None)
  p.add_argument("--output", default="data/stream.jsonl")
  p.add_argument("--align", action="store_true", help="Ollama label alignment (slow)")
  raise SystemExit(asyncio.run(main_async(p.parse_args())))


if __name__ == "__main__":
  main()
