"""Load multi-agent pipeline from sibling multi-agent-llm folder (repo layout)."""

from __future__ import annotations

import sys
from pathlib import Path

from paths import PACKAGE_DIR

_MULTI_AGENT_ROOT = PACKAGE_DIR.parent / "multi-agent-llm"
_imported = False


def ensure_multi_agent_import() -> Path:
    global _imported
    root = _MULTI_AGENT_ROOT.resolve()
    if not root.is_dir():
        raise FileNotFoundError(
            f"Multi-agent folder not found at `{root}`.\n"
            "From the repo root run:\n"
            "  git checkout cursor/multi-agent-standalone-4fea -- multi-agent-llm\n"
            "Or copy the `multi-agent-llm` folder next to `local-llm`."
        )
    root_str = str(root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
    _imported = True
    return root


def multi_agent_config_summary() -> str:
    from pipeline_core import load_config

    ensure_multi_agent_import()
    cfg = load_config()
    return (
        f"**Multi-agent** · Planner `{cfg.model_planner}` · "
        f"Coder `{cfg.model_coder}` · Reviewer `{cfg.model_reviewer}` · "
        f"max {cfg.max_loops} rounds"
    )
