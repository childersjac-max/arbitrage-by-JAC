"""Project paths — ensures .env loads no matter which folder you run from."""

from __future__ import annotations

from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
ENV_FILE = PACKAGE_DIR / ".env"
ENV_EXAMPLE = PACKAGE_DIR / ".env.example"
