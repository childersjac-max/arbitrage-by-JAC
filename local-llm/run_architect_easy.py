#!/usr/bin/env python3
"""
One-command architect run (no web browser needed).

  python run_architect_easy.py
  or double-click scripts/run_architect_easy.bat
"""

from __future__ import annotations

import asyncio
import inspect
import sys

from architect_output import (
    default_mega_prompt_path,
    load_mega_prompt_file,
    save_architect_result,
)
from architect_pipeline import run_architect
from config import get_settings
from ollama_connect import warmup_ollama


def _strip_comment_lines(text: str) -> str:
    lines = []
    for line in text.splitlines():
        if line.strip().startswith("#"):
            continue
        lines.append(line)
    return "\n".join(lines).strip()


async def main() -> int:
    path = default_mega_prompt_path()
    print(f"Reading prompt: {path}")
    mega = _strip_comment_lines(load_mega_prompt_file())
    if not mega:
        print("Error: mega_prompt.txt is empty. Add your project description.")
        return 1

    print("Connecting to Ollama...")
    ok, msg = await warmup_ollama()
    if not ok:
        print(msg)
        return 1
    print(msg)

    settings = get_settings()
    n = settings.architect_max_phases
    print(f"\nRunning architect ({n} phases). This may take 5-15 minutes...\n")

    def progress(step: str) -> None:
        print(f"  >> {step}")

    kwargs: dict = {"max_phases": n}
    if "on_progress" in inspect.signature(run_architect).parameters:
        kwargs["on_progress"] = progress
    else:
        print("  (Tip: git pull for step-by-step progress updates)\n")

    result = await run_architect(mega, **kwargs)

    out_dir = save_architect_result(result)

    print(f"\nSaved to:\n  {out_dir}\n")
    print("Open that folder in File Explorer. Start with README.txt and plan.json.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
