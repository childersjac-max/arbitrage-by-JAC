# Replit not showing GitHub updates?

**Republishing only redeploys whatever code is already inside the Repl.**  
It does **not** automatically pull from GitHub.

## Two separate git histories

Your live deploy commit:

```text
8e89b3f  Published your App   ← what arbitrage-sports-bot.replit.app runs today
```

Our fixes on GitHub (`childersjac-max/arbitrage-by-JAC`):

```text
a491af6  Add History filters, 24h chart, WNBA/PGA/Soccer scan, secure config API
e13281e  Add Replit sync guide
```

Commit `8e89b3f` is **not** on GitHub. Commit `a491af6` was **never** pulled into the Repl before you published.  
So **Publish** kept shipping the old Repl tree.

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
5. **Pull** `main` from GitHub (do not skip this step)
6. Confirm these files exist in the Repl file tree:
   - `artifacts/api-server/src/routes/history.ts`
   - `artifacts/api-server/src/lib/scanner.ts`
   - `artifacts/arb-finder/src/pages/history.tsx`
7. **Deploy → Publish** again (new publish commit will be created; HEAD will **not** stay `8e89b3f`)
8. Hard-refresh browser: `Ctrl+Shift+R`

After a good pull + publish, Version control should show a **new** publish commit whose parent includes `a491af6`, and live `/api/config` must **not** return `oddsjamApiKey`.

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
