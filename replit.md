# BPR Model Dashboard

A sports betting analytics dashboard for sharp bettors. Data-dense, terminal-style UI with three tabs:

## Tabs

- **Line Tracker** (`/`) — Live bet slate from `childersjac-max/Line-Tracker-Model` (GitHub CSV). Shows matchup, book, odds, edge %, EV %, and recommended wager. Filterable by sport. Highlights urgency by hours to game, ARB partner legs, and injured players.
- **NBA Model** (`/nba`) — NBA predictions, bankroll equity curve (recharts), recent bet log, and backtest KPIs (ROI, win rate, Sharpe, max drawdown) from `childersjac-max/nba-betting-model` (GitHub JSON).
- **Arbitrage** (`/arbitrage`) — Live arbitrage opportunities from OddsJam API (requires `ODDSJAM_API_KEY` secret). Auto-refreshes every 30s. Shows margin %, books, and optimal stakes. Gracefully handles missing key.

## Architecture

### Monorepo (pnpm workspaces)

| Package | Path | Purpose |
|---|---|---|
| `@workspace/api-server` | `artifacts/api-server` | Express 5 API, port 8080, serves `/api` |
| `@workspace/dashboard` | `artifacts/dashboard` | React + Vite frontend, port 23183, serves `/` |
| `@workspace/api-spec` | `lib/api-spec` | OpenAPI spec + Orval codegen |
| `@workspace/api-client-react` | `lib/api-client-react` | Generated React Query hooks |
| `@workspace/api-zod` | `lib/api-zod` | Generated Zod schemas |

### API Routes

All routes live under `/api`:

- `GET /api/healthz` — health check
- `GET /api/line-tracker/slate` — fetches + parses `pipeline_output/bet_slate_latest.csv` from GitHub
- `GET /api/line-tracker/patterns` — fetches `pipeline_output/patterns.json` from GitHub
- `GET /api/nba-model/predictions` — fetches `predictions.json` from NBA model GitHub repo
- `GET /api/nba-model/bet-log` — fetches `bet_log.json` from NBA model GitHub repo
- `GET /api/nba-model/backtest` — fetches `backtest.json` from NBA model GitHub repo
- `GET /api/arbitrage/opportunities?sport=&market=` — calls OddsJam API v2

### Route files

- `artifacts/api-server/src/routes/line-tracker.ts` — CSV parser, RFC4180 compliant
- `artifacts/api-server/src/routes/nba-model.ts` — NBA JSON pass-through
- `artifacts/api-server/src/routes/arbitrage.ts` — OddsJam integration, stake calc

### Data Sources

- Line Tracker: `https://raw.githubusercontent.com/childersjac-max/Line-Tracker-Model/main/pipeline_output/bet_slate_latest.csv`
- NBA Model: `https://raw.githubusercontent.com/childersjac-max/nba-betting-model/main/{predictions,bet_log,backtest}.json`
- Arbitrage: `https://api.oddsjam.com/api/v2/arbitrage` (requires `ODDSJAM_API_KEY`)

## Key Implementation Notes

- **No database** — all data is fetched live from external sources on each request
- **Native fetch** — Node 24 global fetch, no `node-fetch` polyfill needed
- **CSV parsing** — RFC4180-compliant parser handles quoted fields, embedded commas, and CRLF
- **`edge_pct` / `ev_pct`** — already in percentage form in the CSV (e.g. `9.19` = 9.19%), NOT 0-1 scale
- **`model_prob`** — 0-1 decimal scale (e.g. `0.48` = 48%)
- **Percentage formatting**: use `formatPct()` for pre-scaled values; use `formatPercent()` for 0-1 scale values
- **Arbitrage margin**: OddsJam returns some margins as 0.012 (normalized to 1.2% in the route handler)

## Environment Secrets

| Secret | Required | Purpose |
|---|---|---|
| `ODDSJAM_API_KEY` | Optional | Enables live arbitrage tab |
| `SESSION_SECRET` | Yes | Express session signing |

## Workflows

- `artifacts/api-server: API Server` — `pnpm run dev` (builds then starts)
- `artifacts/dashboard: web` — `vite --host 0.0.0.0`
