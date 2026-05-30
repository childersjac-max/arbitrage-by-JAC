"""Run one harvester tick and emit unified JSON."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from harvester.orchestrator import HarvesterOrchestrator  # noqa: E402


async def main() -> None:
    """Run a single pipeline tick."""

    orchestrator = HarvesterOrchestrator()
    await orchestrator.run_once()


if __name__ == "__main__":
    asyncio.run(main())
