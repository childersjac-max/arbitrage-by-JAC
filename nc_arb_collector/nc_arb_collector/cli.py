#!/usr/bin/env python3
"""CLI entrypoint for the NC arbitrage collector."""

from __future__ import annotations

import argparse
import json
import logging
import sys

from .orchestrator import NCOrchestrator


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="NC multi-source arbitrage collector (authorized APIs only)",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single collection cycle and print JSON",
    )
    parser.add_argument(
        "--loop",
        type=int,
        default=0,
        help="Run N polling cycles (0 = use --once)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    orch = NCOrchestrator()
    try:
        if args.loop > 0:
            orch.run_loop(iterations=args.loop)
        else:
            result = orch.run_once()
            print(json.dumps(result, indent=2))
    finally:
        orch.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
