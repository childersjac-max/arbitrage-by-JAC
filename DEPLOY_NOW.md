# Deploy updates to arbitrage-sports-bot.replit.app

Code is on GitHub **`main`**. Replit does **not** auto-deploy from GitHub unless you pull first.

## If Publish shows "nix environment failed to build"

See **[docs/REPLIT_NIX_FIX.md](docs/REPLIT_NIX_FIX.md)** — usually: **Recover original configuration files**, `git pull origin main`, confirm `.replit` is Node-only (`nodejs-24`), delete stray `replit.nix`, then Publish again.

## In Replit (required — ~2 minutes)

1. Open https://replit.com/@childersjac/Arbitrage-Sports-Bot  
2. **Version control** → connect **`childersjac-max/arbitrage-by-JAC`** if needed  
3. **Pull** from `main` (latest commit on GitHub)  
4. Shell: `pnpm --filter @workspace/api-server run build` and `pnpm --filter @workspace/arb-finder run build` (both must succeed)  
5. **Deploy** → **Publish**  
6. Hard refresh: https://arbitrage-sports-bot.replit.app/history (`Ctrl+Shift+R`)

## Verify

| URL | Expected |
|-----|----------|
| `/api/config` | `{ "configured": true, ... }` — **no** `oddsjamApiKey` |
| `/api/history/chart?range=today` | `"buckets"` length **24** |
| `/history` | Sport pills: WNBA, Golf, Soccer |

## Rotate secret

After deploy, rotate **`ODDSJAM_API_KEY`** in Replit Secrets (old key was public on `/api/config`).

## Database

If `arb_history` table is missing after pull, run in Replit Shell:

```bash
cd lib/db && pnpm exec drizzle-kit push
```

(Requires `DATABASE_URL` in Secrets.)
