# NC Arbitrage Collector (Python)

**Paid:** The Odds API only (`ODDS_API_KEY`) — DraftKings, FanDuel, BetMGM.

**Free:** Kalshi, PredictIt, ForecastEx CSV, Polymarket Gamma API.

Optic Odds / OddsJam is **not** used. See [`nc_arb_collector/README.md`](../nc_arb_collector/README.md).

```bash
cd nc_arb_collector && pip install -r requirements.txt
export ODDS_API_KEY=...
PYTHONPATH=. python -m nc_arb_collector.cli --once
```
