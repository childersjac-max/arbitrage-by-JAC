# Deploy OddsTerminal to Vercel (GitHub-connected)

Matches the app at [arbitrage-sports-bot.replit.app](https://arbitrage-sports-bot.replit.app/): **arb-finder** UI + **api-server** Express API on one URL.

## 1. Connect GitHub to Vercel

1. Go to [vercel.com](https://vercel.com) → **Add New** → **Project**.
2. Import **`childersjac-max/arbitrage-by-JAC`**.
3. Confirm settings (from `vercel.json`):
   - **Root Directory:** leave empty (repository root — not `artifacts/arb-finder`)
   - **Install:** `pnpm install --no-frozen-lockfile` (full monorepo — not `-w`, which skips workspace packages)
   - **Build:** `pnpm -w run vercel-build`
   - **Output:** `artifacts/arb-finder/dist/public`
4. Add environment variables (Production):

| Variable | Required | Notes |
|----------|----------|--------|
| `ODDSJAM_API_KEY` | Yes | Optic Odds API key |
| `NTFY_TOPIC` | No | Push notifications for alerts |
| `DATABASE_URL` | No | Neon URL if you add Postgres-backed alerts later |

5. Deploy. Future pushes to **`main`** auto-update the same URL.

## 2. Optional: Neon (Postgres)

The live app stores alerts **in memory** on the server. Neon is only needed if you later switch alerts to Postgres (`lib/db`).

1. Create a free project at [neon.tech](https://neon.tech).
2. Run `sql/init.sql` in the SQL editor.
3. Set `DATABASE_URL` in Vercel.

## 3. Smoke test

- `/` — arbitrage dashboard (refreshes ~30s)
- `/api/healthz` — `{ "status": "ok" }`
- `/api/opportunities` — live opportunities (needs `ODDSJAM_API_KEY`)
- `/alerts` — create/delete alert rules

## Architecture on Vercel

- Static SPA: `artifacts/arb-finder`
- All `/api/*` routes: one serverless function (`api/index.ts`) running the Express app from `artifacts/api-server`
