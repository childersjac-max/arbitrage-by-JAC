"""Project paths — ensures .env loads no matter which folder you run from."""

from __future__ import annotations

import shutil
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_DIR.parent
ENV_FILE = PACKAGE_DIR / ".env"
ENV_EXAMPLE = PACKAGE_DIR / ".env.example"


def ensure_env_file() -> Path:
    """Create local-llm/.env from .env.example when missing."""
    if ENV_FILE.is_file():
        return ENV_FILE
    if ENV_EXAMPLE.is_file():
        shutil.copy(ENV_EXAMPLE, ENV_FILE)
        return ENV_FILE
    return ENV_FILE
