# NC Multi-Source Arbitrage Collector

Aggregates odds for **North Carolina–accessible** platforms using **free public APIs** plus your **The Odds API** subscription only.

**No Optic Odds / OddsJam required.**

## Cost model

| Source | Cost | Covers |
|--------|------|--------|
| [The Odds API](https://the-odds-api.com) | **Your subscription** | DraftKings, FanDuel, BetMGM (US region) |
| [Kalshi Trade API v2](https://docs.kalshi.com) | **Free** | CFTC prediction markets (sports series) |
| [PredictIt](https://www.predictit.org/api/marketdata/all/) | **Free** | Politics/sports contracts (1 req/sec) |
| [ForecastEx CSV](https://www.forecastex.com/data) | **Free** | Pairs/prices via `/api/download` |
| [Polymarket Gamma](https://docs.polymarket.com) | **Free** | Sports events via public-search |

### The Odds API quota saver

The collector makes **one request per sport** with `bookmakers=draftkings,fanduel,betmgm` (not three separate calls). Default 7 sports → **7 requests per cycle**, not 21.

## Platforms (5 profiles)

1. **DraftKings** — from The Odds API  
2. **FanDuel** — from The Odds API  
3. **BetMGM** — from The Odds API  
4. **Kalshi** — free API (`KXNFLGAME`, `KXNBAGAME`, etc.)  
5. **PredictIt + ForecastEx + Polymarket** — all free  

## Setup

```bash
cd nc_arb_collector
pip install -r requirements.txt
export ODDS_API_KEY=your_the_odds_api_key
PYTHONPATH=. python -m nc_arb_collector.cli --once
```

Without `ODDS_API_KEY`, free prediction-market sources still run; sportsbook profiles return empty until the key is set.

## Environment

| Variable | Required | Description |
|----------|----------|-------------|
| `ODDS_API_KEY` | For DK/FD/BetMGM | The Odds API key (only paid source) |
| `NC_ARB_SPORT_KEYS` | No | Comma sport keys (default: NFL,NBA,NCAAB,MLB,NHL,MLS,MMA) |
| `NC_ARB_MIN_YIELD_PCT` | No | Min arb % (default `0.5`) |
| `NC_ARB_POLL_SEC` | No | Poll interval (default `45`) |

## Output

Each arbitrage row includes: `timestamp`, `normalized_event_name`, `market_type`, `source_platform_a_odds`, `source_platform_b_odds`, `implied_probability_gap`, `arbitrage_yield_percentage`.

## Architecture

```
Profiles → MarketPackets → SpliceEngine → ArbitragePipeline → JSON
                ↑
    SportsbookCache (1× The Odds API / sport)
    Kalshi / PredictIt / ForecastEx / Polymarket (free)
```

See `nc_arb_collector/sources/free_registry.py` for endpoint catalog.

## Compliance

- Respect PredictIt **1 request/second** limit (enforced in code).
- Do not redistribute PredictIt data commercially.
- The Odds API usage must follow [their terms](https://the-odds-api.com/terms-and-conditions.html).
