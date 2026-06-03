#!/usr/bin/env python3
"""Enable phone/LAN access in local-llm/.env (persists across restarts)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from env_keys import upsert_env_keys  # noqa: E402

KEY = "LOCAL_LLM_UI_LAN"


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    env_path = root / ".env"
    example = root / ".env.example"
    upsert_env_keys(env_path, example, {KEY: "1"})
    print(f"Set {KEY}=1 in {env_path}")
    print("Restart: python web_app.py")
    print("Startup will print a http://192.168.x.x:7860 URL for your phone (same Wi-Fi).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
