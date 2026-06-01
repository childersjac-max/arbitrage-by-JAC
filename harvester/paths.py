"""Repository paths for the harvester package."""

from __future__ import annotations

from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_DIR.parent
LOCAL_LLM_DIR = REPO_ROOT / "local-llm"
GENERATED_DIR = PACKAGE_DIR / "generated"
ENV_FILE = PACKAGE_DIR / ".env"
ENV_EXAMPLE = PACKAGE_DIR / ".env.example"
