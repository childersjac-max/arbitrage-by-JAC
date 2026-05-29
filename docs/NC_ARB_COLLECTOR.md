# NC Arbitrage Collector (Python)

See [`nc_arb_collector/README.md`](../nc_arb_collector/README.md) for setup, architecture, and compliance notes.

Quick start:

```bash
cd nc_arb_collector
pip install -r requirements.txt
export ODDS_API_KEY=your_the_odds_api_key
PYTHONPATH=. python -m nc_arb_collector.cli --once
```

This complements the production Node stack (`artifacts/api-server`) which uses Optic Odds + Kalshi.
