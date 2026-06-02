#!/usr/bin/env python3
"""Set LOCAL_LLM_PERFORMANCE_PROFILE in local-llm/.env (one command)."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

PROFILES = ("fast", "balanced", "quality")


def main() -> int:
    parser = argparse.ArgumentParser(description="Switch CPU performance profile")
    parser.add_argument(
        "profile",
        choices=PROFILES,
        nargs="?",
        default="balanced",
        help="fast | balanced | quality",
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    env_path = root / ".env"
    example = root / ".env.example"
    key = "LOCAL_LLM_PERFORMANCE_PROFILE"
    line = f"{key}={args.profile}\n"

    if env_path.is_file():
        text = env_path.read_text(encoding="utf-8")
        if re.search(rf"^{re.escape(key)}=", text, flags=re.MULTILINE):
            text = re.sub(rf"^{re.escape(key)}=.*$", line.strip(), text, flags=re.MULTILINE)
        else:
            text = text.rstrip() + "\n" + line
        env_path.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")
    elif example.is_file():
        text = example.read_text(encoding="utf-8")
        if re.search(rf"^{re.escape(key)}=", text, flags=re.MULTILINE):
            text = re.sub(rf"^{re.escape(key)}=.*$", line.strip(), text, flags=re.MULTILINE)
        else:
            text = text.rstrip() + "\n" + line
        env_path.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")
    else:
        env_path.write_text(line, encoding="utf-8")

    print(f"Set {key}={args.profile} in {env_path}")
    print("Restart web_app.py if it is running.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
