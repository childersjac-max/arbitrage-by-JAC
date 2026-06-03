"""
Find harvester/ and run arbitrage_orchestrator.py from any working directory.

Used by repo-root and sports_arbitrage_pipeline/ entry scripts.
"""

from __future__ import annotations

import os
import runpy
import sys
from pathlib import Path


def _load_local_env() -> None:
    root = Path(__file__).resolve().parent
    for env_file in (root / "sports_arbitrage_pipeline" / "local.env", root / "local.env"):
        if not env_file.is_file():
            continue
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("HARVESTER_ROOT="):
                os.environ.setdefault("HARVESTER_ROOT", line.split("=", 1)[1].strip())
                return


def find_harvester_dir(start: Path | None = None) -> Path:
    """Return harvester/ directory containing arbitrage_orchestrator.py."""
    _load_local_env()
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
        here / "arbitrage-by-JAC" / "harvester",
        Path.home() / "Projects" / "arbitrage-by-JAC" / "harvester",
        Path.home() / "arbitrage-by-JAC" / "harvester",
    ]
    seen: set[Path] = set()
    for base in candidates:
        base = base.resolve()
        if base in seen:
            continue
        seen.add(base)
        if (base / "arbitrage_orchestrator.py").is_file():
            return base

    raise FileNotFoundError(
        "Could not find harvester/arbitrage_orchestrator.py.\n\n"
        "Fix:\n"
        "  1. Clone the full repo:\n"
        "       git clone https://github.com/childersjac-max/arbitrage-by-JAC.git\n"
        "       cd arbitrage-by-JAC/sports_arbitrage_pipeline\n"
        "  2. Or set HARVESTER_ROOT to your harvester folder, e.g.:\n"
        "       export HARVESTER_ROOT=~/Projects/arbitrage-by-JAC/harvester\n"
    )


def run_harvester_orchestrator(argv: list[str] | None = None) -> None:
    harvester = find_harvester_dir()
    script = harvester / "arbitrage_orchestrator.py"
    if argv is not None:
        sys.argv = [str(script), *argv[1:]]
    os.chdir(harvester)
    sys.path.insert(0, str(harvester))
    runpy.run_path(str(script), run_name="__main__")
