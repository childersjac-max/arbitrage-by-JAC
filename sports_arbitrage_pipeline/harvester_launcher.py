"""Find harvester/ and run arbitrage_orchestrator.py (standalone copy for this folder)."""

from __future__ import annotations

import os
import runpy
import sys
from pathlib import Path


def _load_local_env() -> None:
    env_file = Path(__file__).resolve().parent / "local.env"
    if not env_file.is_file():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        if key == "HARVESTER_ROOT" and value.strip():
            os.environ.setdefault("HARVESTER_ROOT", value.strip())


def find_harvester_dir(start: Path | None = None) -> Path:
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
        here.parent / "arbitrage-by-JAC" / "harvester",
        here.parent.parent / "arbitrage-by-JAC" / "harvester",
        Path.home() / "Projects" / "arbitrage-by-JAC" / "harvester",
        Path.home() / "arbitrage-by-JAC" / "harvester",
        Path.home() / "sports_arbitrage_pipeline" / "arbitrage-by-JAC" / "harvester",
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
