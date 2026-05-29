"""CLI entrypoint."""

from __future__ import annotations

import argparse
import json
import sys

from dotenv import load_dotenv

from arb_harvest.config import HarvestConfig
from arb_harvest.engine import HarvestOrchestrator


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="Harvest odds (The Odds API + public prediction markets) and detect arbs.",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single cycle and print JSON to stdout",
    )
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Poll continuously (default interval from ARB_POLL_INTERVAL_SEC)",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Write JSON payload to file (implies --once if neither loop/once set)",
    )
    args = parser.parse_args(argv)

    config = HarvestConfig.from_env()
    if not config.odds_api_key:
        print("ERROR: Set ODDS_API_KEY in environment or .env", file=sys.stderr)
        return 1

    orch = HarvestOrchestrator(config)

    if args.loop:
        orch.run_loop()
        return 0

    payload = orch.run_once()
    text = json.dumps(payload, indent=2)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(text)
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
