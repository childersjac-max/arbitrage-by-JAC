"""CLI pipeline: harvest → JSON stdout / file."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from harvest.orchestrator import HarvestOrchestrator


def run_pipeline(*, outfile: Path | None = None) -> int:
    rows = HarvestOrchestrator().run()
    payload = [r.to_dict() for r in rows]
    text = json.dumps(payload, indent=2)
    if outfile:
        outfile.write_text(text)
    else:
        sys.stdout.write(text + "\n")
    return 0
