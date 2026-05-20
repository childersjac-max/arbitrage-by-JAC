# Replit not showing GitHub updates?

**Republishing only redeploys whatever code is already inside the Repl.**  
It does **not** automatically pull from GitHub.

## How to tell you're on the old build

| Check | Old (current live) | New (commit `a491af6`) |
|-------|-------------------|------------------------|
| `GET /api/config` | Returns `oddsjamApiKey` | Returns `configured`, `ntfyEnabled` only |
| `GET /api/history/chart?range=today` | ~8–12 sparse buckets | **24** buckets (12 AM–11 PM) |
| History page | No WNBA / sport pills | Sport + league filter rows |
| JS bundle | `index-BHznIPEq.js` | New hash after rebuild |

## Fix (do this in Replit, then Publish)

### If the Repl is linked to GitHub

1. Open [Arbitrage-Sports-Bot](https://replit.com/@childersjac/Arbitrage-Sports-Bot)
2. **Tools → Version control** (or Git icon)
3. Confirm remote: `childersjac-max/arbitrage-by-JAC`
4. Click **Pull** (or Fetch + Merge) from `main`
5. Wait until you see commit: `Add History filters, 24h chart...` (`a491af6`)
6. **Deploy → Publish** again
7. Hard-refresh browser: `Ctrl+Shift+R`

### If the Repl is NOT linked to GitHub

**Option A — Connect repo**

1. Version control → **Connect to GitHub**
2. Select **`childersjac-max/arbitrage-by-JAC`**
3. Pull `main`, then Publish

**Option B — Replace from GitHub in Cursor, then push from Replit**

1. In this Repl, connect the same GitHub repo
2. Pull `main` so Repl files match GitHub

## After a successful deploy

```bash
# In browser or terminal:
curl https://arbitrage-sports-bot.replit.app/api/config
# Should NOT contain oddsjamApiKey

curl "https://arbitrage-sports-bot.replit.app/api/history/chart?range=today" | jq '.buckets | length'
# Should print 24
```

## Rotate API key

The old build exposed your OddsJam key on `/api/config`.  
Rotate **`ODDSJAM_API_KEY`** in Replit Secrets even after you deploy the fix.
