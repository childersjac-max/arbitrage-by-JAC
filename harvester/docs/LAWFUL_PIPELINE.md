# Lawful ingestion pipeline (what we build vs what we do not)

## Your Sources tab is working

- **Successfully loaded** = data came from **The Odds API** for that US book.
- **Not connected** = no official API wired yet (Kalshi, Polymarket, bet365 direct, exchanges).
- **No odds returned** = book not in that API response (region, sport, or quota).

We **do not** implement stealth scraping, TLS fingerprint spoofing, Playwright anti-bot bypass, or proxy rotation to harvest sportsbook sites without permission.

## What is implemented

| Module | Role |
|--------|------|
| `integrator_factory.py` | Registry for all 14 platforms |
| `models_depth.py` | Schemas for lines, order books, exchange depth |
| `arbitrage_orchestrator.py` | `asyncio` fetch + merge + JSON snapshot |
| `fuzzy_normalizer.py` | Ollama entity mapping (optional) |
| `integrators/odds_api.py` | Lawful US books via your paid API |

## Data depth limits (honest)

**The Odds API** provides main h2h, spreads, and totals for many US books. It does **not** provide:

- 10+ alternate spread/total ladders per book
- Full player prop ladders (15 players × stats)
- Kalshi/Polymarket order book depth
- Betfair/Smarkets/SportX back/lay stacks

Those require each platform’s **official API** (or a licensed commercial feed), implemented in `integrators/stubs.py` when you have keys.

## Run orchestrator

```bash
cd harvester
source .venv/Scripts/activate
python arbitrage_orchestrator.py --sport basketball_nba --markets h2h spreads totals
```

Output: `data/ingestion_snapshot.json`

## More events in the dashboard

1. Set in `.env`: `ODDS_API_MARKETS=h2h,spreads,totals`
2. Confirm sport key: `HARVESTER_DEFAULT_SPORT=basketball_nba`
3. Check API quota on the-odds-api.com (each market costs credits)
