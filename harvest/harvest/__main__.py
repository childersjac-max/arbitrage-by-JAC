"""python -m harvest"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from dotenv import load_dotenv

from harvest.pipeline import run_pipeline


def main() -> None:
    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description="Multi-source arbitrage harvest pipeline")
    parser.add_argument("-o", "--output", type=Path, help="Write JSON to file instead of stdout")
    args = parser.parse_args()
    raise SystemExit(run_pipeline(outfile=args.output))


if __name__ == "__main__":
    main()
