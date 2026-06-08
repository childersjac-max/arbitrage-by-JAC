"""Load multi-agent pipeline from sibling multi-agent-llm folder (repo layout)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

from paths import PACKAGE_DIR

_MULTI_AGENT_ROOT = PACKAGE_DIR.parent / "multi-agent-llm"
_pipeline_core: ModuleType | None = None


def multi_agent_root() -> Path:
    root = _MULTI_AGENT_ROOT.resolve()
    if not root.is_dir():
        raise FileNotFoundError(
            f"Multi-agent folder not found at `{root}`.\n"
            "Expected layout:\n"
            "  arbitrage-by-JAC/local-llm/\n"
            "  arbitrage-by-JAC/multi-agent-llm/\n\n"
            "Fix: git checkout cursor/gradio-multi-agent-4fea -- multi-agent-llm"
        )
    return root


def get_pipeline_core() -> ModuleType:
    """Import pipeline_core from ../multi-agent-llm (explicit path — works on Windows)."""
    global _pipeline_core
    if _pipeline_core is not None:
        return _pipeline_core

    root = multi_agent_root()
    core_file = root / "pipeline_core.py"
    if not core_file.is_file():
        raise FileNotFoundError(
            f"Missing `{core_file}`.\n"
            "Run from repo root:\n"
            "  git fetch origin cursor/gradio-multi-agent-4fea\n"
            "  git checkout cursor/gradio-multi-agent-4fea -- multi-agent-llm"
        )

    root_str = str(root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)

    spec = importlib.util.spec_from_file_location("pipeline_core", core_file)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load pipeline from {core_file}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["pipeline_core"] = module
    spec.loader.exec_module(module)
    _pipeline_core = module
    return module


def ensure_multi_agent_import() -> Path:
    """Backward-compatible alias."""
    get_pipeline_core()
    return multi_agent_root()


def multi_agent_config_summary() -> str:
    pc = get_pipeline_core()
    cfg = pc.load_config()
    return (
        f"**Multi-agent** · Planner `{cfg.model_planner}` · "
        f"Coder `{cfg.model_coder}` · Reviewer `{cfg.model_reviewer}` · "
        f"max {cfg.max_loops} rounds"
    )
