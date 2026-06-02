#!/usr/bin/env python3
"""Enable phone/LAN access in local-llm/.env (persists across restarts)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

KEY = "LOCAL_LLM_UI_LAN"


def _upsert_env(env_path: Path, example: Path, value: str) -> None:
    line = f"{KEY}={value}\n"
    if env_path.is_file():
        text = env_path.read_text(encoding="utf-8")
    elif example.is_file():
        text = example.read_text(encoding="utf-8")
    else:
        text = ""

    if re.search(rf"^{re.escape(KEY)}=", text, flags=re.MULTILINE):
        text = re.sub(rf"^{re.escape(KEY)}=.*$", line.strip(), text, flags=re.MULTILINE)
    else:
        text = text.rstrip() + "\n" + line
    env_path.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    env_path = root / ".env"
    example = root / ".env.example"
    _upsert_env(env_path, example, "1")
    print(f"Set {KEY}=1 in {env_path}")
    print("Restart: python web_app.py")
    print("Startup will print a http://192.168.x.x:7860 URL for your phone (same Wi-Fi).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
