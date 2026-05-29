# Harvest — multi-source arbitrage data plane

Python package that collects odds from **licensed and public APIs**, splices uneven feeds, fuzzy-matches events, and emits a unified arbitrage board JSON schema.

## Quick start

```bash
cd harvest
pip install -r requirements.txt
export ODDSJAM_API_KEY=your_optic_odds_key   # optional; enables 7 US sportsbooks
PYTHONPATH=. python3 -m harvest
```

## Output schema

Each row:

```json
{
  "timestamp": "2026-05-29T12:00:00+00:00",
  "normalized_event_name": "Hornets @ Lakers",
  "market_type": "Moneyline",
  "source_A": { "platform": "draftkings", "odds": 150, "liquidity_volume": null },
  "source_B": { "platform": "kalshi", "odds": -140, "liquidity_volume": null },
  "arbitrage_yield_percentage": 1.25
}
```

## Architecture

See [docs/HARVEST_ARCHITECTURE.md](docs/HARVEST_ARCHITECTURE.md) and [docs/SOURCE_MATRIX.md](docs/SOURCE_MATRIX.md).

## Compliance

This package **does not** implement anti-bot evasion, TLS fingerprint spoofing for stealth, residential proxy rotation to bypass blocks, or scraping of consumer sites against terms of service. Use official APIs and licensed aggregators (Optic Odds, exchange developer programs).

The existing Node scanner in `artifacts/api-server` mirrors the same sources for production.
