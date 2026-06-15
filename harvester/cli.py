#!/usr/bin/env python3
"""CLI for the harvester arbitrage pipeline."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

from config import get_settings
from engine import HarvesterEngine
from integrators.odds_api import OddsApiIntegrator
from integrators.stubs import STUB_INTEGRATORS


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s %(message)s")


async def _cmd_run(args: argparse.Namespace) -> int:
    engine = HarvesterEngine()
    records = await engine.run(args.sport, arbs_only=args.arbs_only)
    payload = [r.to_export_dict() for r in records]
    if args.output:
        args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"Wrote {len(payload)} records to {args.output}")
    else:
        print(json.dumps(payload, indent=2))
    return 0


async def _cmd_health(args: argparse.Namespace) -> int:
    integrator = OddsApiIntegrator()
    try:
        ok, msg = await integrator.health_check()
    finally:
        await integrator.close()
    print(f"the_odds_api: {'OK' if ok else 'FAIL'} — {msg}")
    if args.stubs:
        for name, stub in STUB_INTEGRATORS.items():
            s_ok, s_msg = await stub.health_check()
            print(f"  {name}: {'stub' if not s_ok else 'ok'} — {s_msg}")
    return 0 if ok else 1


async def _cmd_list_stubs(_: argparse.Namespace) -> int:
    for name, stub in sorted(STUB_INTEGRATORS.items()):
        notes = stub.integration_notes()
        print(f"{name}: {notes.get('integration_path', '')}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Sports arbitrage harvester")
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Fetch odds, normalize, detect arbitrage")
    run_p.add_argument("--sport", default=None, help="Sport key (default from env)")
    run_p.add_argument("--arbs-only", action="store_true", help="Only output records with arb")
    run_p.add_argument("-o", "--output", type=Path)
    run_p.set_defaults(func=_cmd_run)

    health_p = sub.add_parser("health", help="Check The Odds API connectivity")
    health_p.add_argument("--stubs", action="store_true", help="Also list stub integrators")
    health_p.set_defaults(func=_cmd_health)

    stubs_p = sub.add_parser("list-stubs", help="Show stub platform integration notes")
    stubs_p.set_defaults(func=_cmd_list_stubs)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    _configure_logging(args.verbose)
    settings = get_settings()
    if args.command == "run" and not settings.odds_api_key:
        print("Error: set ODDS_API_KEY in harvester/.env", file=sys.stderr)
        return 1
    return asyncio.run(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
