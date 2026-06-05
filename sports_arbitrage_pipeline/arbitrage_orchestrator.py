#!/usr/bin/env python3
"""Entry point for sports_arbitrage_pipeline — runs harvester/arbitrage_orchestrator.py."""

from harvester_launcher import run_harvester_orchestrator

if __name__ == "__main__":
    run_harvester_orchestrator()
