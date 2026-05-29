# Source matrix — 14 targets

| # | Platform | Type | Harvest module | Access path |
|---|----------|------|----------------|-------------|
| 1 | DraftKings | US sportsbook | `optic_odds.py` | Optic Odds API (`ODDSJAM_API_KEY`) |
| 2 | FanDuel | US sportsbook | `optic_odds.py` | Same |
| 3 | BetMGM | US sportsbook | `optic_odds.py` | Same |
| 4 | Caesars | US sportsbook | `optic_odds.py` | Same |
| 5 | Fanatics | US sportsbook | `optic_odds.py` | Same |
| 6 | bet365 | US sportsbook | `optic_odds.py` | Same |
| 7 | theScore | US sportsbook | `optic_odds.py` | Same |
| 8 | Kalshi | US prediction market | `kalshi.py` | `GET https://api.elections.kalshi.com/trade-api/v2/markets` |
| 9 | Polymarket | Global prediction | `polymarket.py` | Gamma `https://gamma-api.polymarket.com/markets`; CLOB `https://clob.polymarket.com/book` |
| 10 | DraftKings Predictions | US prediction | `stubs.py` | Partner API — register with DK; no public scrape |
| 11 | FanDuel Predicts | US prediction | `stubs.py` | Partner API |
| 12 | Betfair Exchange | P2P exchange | `betfair.py` | [Betfair Developer](https://docs.developer.betfair.com/) — `BETFAIR_APP_KEY`, session token |
| 13 | Smarkets | P2P exchange | `stubs.py` | `SMARKETS_API_KEY` |
| 14 | SportX / SX Bet | P2P exchange | `stubs.py` | `SPORTX_API_KEY` |

## Markets covered

| Family | Market types |
|--------|----------------|
| Sportsbooks (via Optic) | Moneyline, spreads, totals, player props |
| Prediction markets | Yes/No contracts, implied prob → American |
| Exchanges | Back/lay best offers, liquidity size |

## Why not “hidden endpoints”?

Consumer sportsbook sites protect odds with bot management and contractual restrictions. Documented, sustainable approaches:

1. **Licensed aggregator** (Optic Odds) for multi-book US lines in one API.
2. **Public/regulated APIs** (Kalshi, Polymarket Gamma/CLOB read).
3. **Exchange developer programs** (Betfair, Smarkets, SportX) for order books.

Reverse-engineering mobile app GraphQL or spoofing Chrome JA3 to mimic retail users violates platform ToS and creates brittle pipelines — excluded by design.

## Environment variables

```bash
ODDSJAM_API_KEY=          # Optic Odds (7 sportsbooks)
BETFAIR_APP_KEY=
BETFAIR_SESSION_TOKEN=
SMARKETS_API_KEY=         # future
SPORTX_API_KEY=           # future
```
