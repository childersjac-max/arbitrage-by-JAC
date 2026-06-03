"""Find harvester/ and run arbitrage_orchestrator.py (standalone copy for this folder)."""

from __future__ import annotations

import os
import runpy
import sys
from pathlib import Path


def find_harvester_dir(start: Path | None = None) -> Path:
    env_root = os.environ.get("HARVESTER_ROOT", "").strip()
    if env_root:
        candidate = Path(env_root).expanduser().resolve()
        if (candidate / "arbitrage_orchestrator.py").is_file():
            return candidate
        if (candidate / "harvester" / "arbitrage_orchestrator.py").is_file():
            return candidate / "harvester"

    here = (start or Path(__file__).resolve().parent).resolve()
    candidates: list[Path] = [
        here / "harvester",
        here.parent / "harvester",
        here.parent.parent / "harvester",
        Path.home() / "Projects" / "arbitrage-by-JAC" / "harvester",
        Path.home() / "arbitrage-by-JAC" / "harvester",
    ]
    seen: set[Path] = set()
    for base in candidates:
        try:
            base = base.resolve()
        except OSError:
            continue
        if base in seen:
            continue
        seen.add(base)
        if (base / "arbitrage_orchestrator.py").is_file():
            return base

    raise FileNotFoundError(
        "Could not find harvester/arbitrage_orchestrator.py.\n\n"
        "Clone the full repo or set HARVESTER_ROOT:\n"
        "  export HARVESTER_ROOT=~/Projects/arbitrage-by-JAC/harvester\n"
    )


def run_harvester_orchestrator(argv: list[str] | None = None) -> None:
    harvester = find_harvester_dir()
    script = harvester / "arbitrage_orchestrator.py"
    if argv is not None:
        sys.argv = [str(script), *argv[1:]]
    os.chdir(harvester)
    sys.path.insert(0, str(harvester))
    runpy.run_path(str(script), run_name="__main__")
