#!/usr/bin/env python3
"""Enable away-from-home access (Gradio public link + password in .env)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from remote_access import ensure_remote_credentials  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Enable remote access (public gradio.live URL with login)",
    )
    parser.add_argument("--user", default="admin", help="Login username (default: admin)")
    parser.add_argument(
        "--password",
        default=None,
        help="Login password (default: random, saved to .env)",
    )
    parser.add_argument(
        "--if-missing",
        action="store_true",
        help="Do not change an existing password (used by run_remote.bat)",
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    env_path = root / ".env"
    example = root / ".env.example"
    user, pwd = ensure_remote_credentials(
        env_path,
        example,
        user=args.user,
        password=args.password,
        only_if_missing=args.if_missing,
    )
    print(f"Updated {env_path}")
    print("  LOCAL_LLM_UI_SHARE=1")
    print(f"  LOCAL_LLM_UI_AUTH_USER={user}")
    if args.if_missing and args.password is None:
        print("  LOCAL_LLM_UI_AUTH_PASSWORD=(unchanged — see .env)")
    else:
        print(f"  LOCAL_LLM_UI_AUTH_PASSWORD={pwd}")
    print("\nStart the app:  python web_app.py")
    print("Or:             scripts\\run_remote.bat")
    print("\nOn startup you will get a https://….gradio.live URL — use that on your phone anywhere.")
    print("Keep this PC on with Ollama running. Do not commit .env to git.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
