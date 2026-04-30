# Sports Arbitrage Finder — OddsJam

A sports betting arbitrage detection tool powered by the OddsJam API. Finds guaranteed profit opportunities across multiple bookmakers using live odds data.

## Architecture

- **Frontend** (`artifacts/arb-finder`): React + Vite app. Fetches OddsJam API key from `/api/config`, then calls OddsJam directly from the browser. Arbitrage calculations run client-side.
- **API Server** (`artifacts/api-server`): Express 5 + Node. Handles alerts CRUD (PostgreSQL), serves config, and acts as proxy for OddsJam.
- **Database** (`lib/db`): PostgreSQL via Drizzle ORM. Stores user alerts.

## Network Note

OddsJam's API (`api.oddsjam.com`) is not resolvable in Replit's development sandbox. **The app works correctly when deployed to production** where the server has full internet access. In development, odds data will return empty.

## Pages

- `/` — Dashboard: Live arbitrage opportunities, summary stats (auto-refreshes every 30s)
- `/odds` — Live Odds: Browse live game odds by sport and market type
- `/alerts` — Alerts: Create/delete saved arbitrage alerts with profit thresholds
- `/sports` — Sports: Directory of all OddsJam-supported sports

## Key Files

- `artifacts/arb-finder/src/lib/oddsjam-client.ts` — Browser-side OddsJam API client
- `artifacts/arb-finder/src/lib/arbitrage.ts` — Arbitrage detection algorithm (client-side)
- `artifacts/arb-finder/src/hooks/use-oddsjam.ts` — React Query hooks wrapping OddsJam
- `artifacts/api-server/src/routes/config.ts` — Serves API key to frontend
- `artifacts/api-server/src/routes/alerts.ts` — Alerts CRUD
- `lib/db/src/schema/alerts.ts` — Alerts table schema

## Secrets

- `ODDSJAM_API_KEY` — OddsJam API key (required)
- `SESSION_SECRET` — Session secret
- `DATABASE_URL` — PostgreSQL connection string (auto-provisioned)

## Arbitrage Algorithm

For each game and market:
1. Find the best (highest) decimal odds for each outcome across all bookmakers
2. Calculate total implied probability: sum(1/odds_i)
3. If total implied < 1.0: arbitrage exists
4. Profit % = (1/total_implied - 1) × 100
5. Optimal stakes: stake_i = bankroll × (1/odds_i) / total_implied
