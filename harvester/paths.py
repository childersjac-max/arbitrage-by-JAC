"""Backward-compatible shim — use harvester_paths.py."""

from harvester_paths import (
    ENV_EXAMPLE,
    ENV_FILE,
    GENERATED_DIR,
    LOCAL_LLM_DIR,
    PACKAGE_DIR,
    REPO_ROOT,
)

__all__ = [
    "ENV_EXAMPLE",
    "ENV_FILE",
    "GENERATED_DIR",
    "LOCAL_LLM_DIR",
    "PACKAGE_DIR",
    "REPO_ROOT",
]
