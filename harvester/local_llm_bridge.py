"""Import local-llm modules without shadowing harvester's removed config/paths names."""

from __future__ import annotations

import sys
from typing import Any

from harvester_paths import LOCAL_LLM_DIR, PACKAGE_DIR

# Modules that exist in both trees with different meanings
_SHADOW_NAMES = frozenset(
    {
        "config",
        "paths",
        "ollama_connect",
        "local_inference",
        "normalization_prompt",
        "prompt_loader",
        "prompt_types",
    }
)


def _harvester_dir() -> str:
    return str(PACKAGE_DIR.resolve()).replace("\\", "/")


def _purge_shadow_modules() -> None:
    """Drop cached harvester copies so local-llm can register its own modules."""
    hdir = _harvester_dir()
    for name in list(sys.modules):
        if name not in _SHADOW_NAMES:
            continue
        mod = sys.modules.get(name)
        path = getattr(mod, "__file__", None) or ""
        path = path.replace("\\", "/")
        if hdir in path:
            del sys.modules[name]


def prepare_local_llm_path() -> None:
    _purge_shadow_modules()
    root = str(LOCAL_LLM_DIR.resolve())
    if root not in sys.path:
        sys.path.insert(0, root)
    elif sys.path[0] != root:
        try:
            sys.path.remove(root)
        except ValueError:
            pass
        sys.path.insert(0, root)


def import_local_llm(module_name: str) -> Any:
    prepare_local_llm_path()
    import importlib

    return importlib.import_module(module_name)
