# Deploy OddsTerminal to Vercel + Neon

One stable URL (e.g. `https://your-app.vercel.app`) that auto-updates on every push to `main`.

## 1. Neon (free Postgres for Alerts)

1. Sign in at [neon.tech](https://neon.tech) and create a project.
2. Copy the **connection string** (use the *pooled* URL if offered).
3. In the Neon SQL editor, run:

```sql
CREATE TABLE IF NOT EXISTS alerts (
  id serial PRIMARY KEY,
  sport text,
  market text,
  min_profit_percent numeric(10, 4) NOT NULL DEFAULT '0',
  created_at timestamp NOT NULL DEFAULT now()
);
```

Alternatively, from this repo with `DATABASE_URL` set:

```bash
pnpm db:push
```

## 2. Vercel (connect GitHub)

1. Sign in at [vercel.com](https://vercel.com) → **Add New Project**.
2. Import `childersjac-max/arbitrage-by-JAC` from GitHub.
3. Vercel should detect settings from `vercel.json`:
   - **Build Command:** `pnpm --filter @workspace/arb-finder run build`
   - **Output Directory:** `artifacts/arb-finder/dist`
   - **Install Command:** `pnpm install`
4. Add **Environment Variables** (Production + Preview):

| Name | Value |
|------|--------|
| `ODDSJAM_API_KEY` | Your Optic Odds / OddsJam API key |
| `DATABASE_URL` | Neon connection string |
| `SESSION_SECRET` | Any random string (optional) |

5. Click **Deploy**.

Every push to `main` triggers a new production deployment at the same URL.

## 3. Verify

- `https://<your-app>.vercel.app/` — arbitrage dashboard
- `https://<your-app>.vercel.app/api/healthz` — `{ "status": "ok" }`
- `https://<your-app>.vercel.app/api/config` — returns API key shape (requires `ODDSJAM_API_KEY`)
- Alerts page — requires `DATABASE_URL` + `alerts` table

## Local dev (optional)

```bash
pnpm install
cp .env.example .env   # fill in keys
pnpm --filter @workspace/api-server run dev   # API on :3001 (set PORT=3001)
pnpm --filter @workspace/arb-finder run dev   # UI on :5173, proxies /api
```
