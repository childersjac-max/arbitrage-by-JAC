# OddsTerminal — Data Sources & Architecture

Source of truth for **production** (`arbitrage-sports-bot.replit.app`, Replit publish `8e89b3f`).  
GitHub `main` (`a491af6`) is a **partial fork** — do not deploy it over production without merging.

## Live odds / game data

| Source | Endpoint / module | Auth | Role |
|--------|-------------------|------|------|
| **Optic Odds** | `artifacts/api-server/src/lib/oddsjam.ts` → `api.opticodds.com` (v3) | `ODDSJAM_API_KEY` | Primary sportsbook odds (NC books: DK, FD, BetMGM, Caesars, bet365, Fanatics, theScore) |
| **Kalshi** | `artifacts/api-server/src/lib/kalshi.ts` | None | Prediction market → American odds |
| **Polymarket** | `artifacts/api-server/src/lib/prediction-markets.ts` | None | Same pattern |
| **Manifold** | `prediction-markets.ts` | None | Same pattern |

**Dev constraint:** `api.oddsjam.com` may not resolve in Replit’s dev sandbox → empty Optic Odds in dev. Production deploy works. Kalshi/Polymarket reachable in dev.

## Database

- **PostgreSQL** via `DATABASE_URL` (Replit-managed)
- **Drizzle** schema: `lib/db/src/schema/`
- Table **`arb_history`** — every arb the background monitor detects (powers `/api/history/chart`)

## Push alerts

- **ntfy.sh** — `NTFY_TOPIC` (e.g. `JAC_ARB_ALERT`)
- Monitor POSTs `https://ntfy.sh/{topic}` on new arbs

## Backend (`artifacts/api-server`, Express 5, Node 24)

| Route | Purpose |
|-------|---------|
| `GET /api/opportunities` | Live arb detection: Optic Odds + Kalshi + Polymarket (+ Manifold) |
| `GET /api/tracked-games` | Merged game list (all sources), next N days |
| `GET /api/odds` | Raw sportsbook odds (Optic Odds only) |
| `GET /api/history/chart` | Time-series from **`arb_history`** |
| `GET /api/alerts` | CRUD alert thresholds |
| `GET /api/sports` | Sports list from Optic Odds |

**Background monitor (~60s):** writes arbs → `arb_history`, optional ntfy.

**Deploy:** autoscale — API `pnpm --filter @workspace/api-server run build` → `node artifacts/api-server/dist/index.mjs`; frontend static from `artifacts/arb-finder/dist/public`.

## Frontend (`artifacts/arb-finder`, React + Vite)

Pages: **Arbitrage**, **Live Odds**, **Alerts**, **History**.

## GitHub vs Replit (why Publish didn’t show updates)

| | Replit `8e89b3f` (live) | GitHub `a491af6` |
|--|-------------------------|------------------|
| Kalshi / Polymarket | Yes | **No** |
| `arb_history` (Postgres) | Yes | In-memory only |
| `/api/tracked-games` | Yes | **No** |
| History sport filters + 24h axis | **No** | Yes |
| Secure `/api/config` | **No** (leaks key) | Yes |
| WNBA / PGA / Soccer scan | Partial | Yes (Optic only) |

**Do not Pull GitHub `main` over Replit** — you would lose prediction markets and DB history.

## Correct sync direction

1. **Replit → Push to GitHub** (export production to `childersjac-max/arbitrage-by-JAC`, branch e.g. `replit-production`).
2. Apply **targeted patches** (History filters, 24 buckets, sport/league query params, secure config, extra scan leagues) on top of that tree.
3. **Pull** merged branch in Replit → **Publish**.

See `docs/MERGE_PLAN.md` and `docs/patches/`.
