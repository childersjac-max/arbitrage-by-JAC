# Merge plan: History + scan updates **on** production code

## Problem

- Live deploy = Replit commit **`8e89b3f`**
- Our fixes = GitHub **`a491af6`** (never merged into Replit)
- Pulling GitHub **onto** Replit would **remove** Kalshi, Polymarket, `arb_history`, `/api/tracked-games`

## Step 1 — Put production on GitHub (you, in Replit)

1. Open **Arbitrage-Sports-Bot** → **Version control**
2. **Connect** to `childersjac-max/arbitrage-by-JAC` (if not already)
3. **Push** Repl → GitHub (prefer branch `replit-production` if you want to keep old `main` safe)
4. Tell Cursor the branch name — we patch that branch

## Step 2 — Patches to apply (after Step 1)

### A. Secure config

**File:** `artifacts/api-server/src/routes/config.ts` (or equivalent)

Stop returning `oddsjamApiKey`. Return only:

```json
{ "configured": true, "ntfyEnabled": true }
```

Rotate `ODDSJAM_API_KEY` in Secrets after deploy.

### B. History chart — 24 buckets + sport/league filters

**Files:**

- Add `artifacts/api-server/src/lib/history-chart.ts` (from `docs/patches/history-chart.ts`)
- Update `artifacts/api-server/src/routes/history.ts`:
  - Query params: `range`, `sport`, `league`
  - Load rows from **`arb_history`** (not sparse in-memory only)
  - Call `buildHistoryChart(range, sport, league, rows)`
  - Include `sportFilters` / `leagueFilters` in JSON response

**Today** must return **24** hourly buckets with `label`: `12 AM` … `11 PM`.

### C. Frontend History page

**File:** `artifacts/arb-finder/src/pages/history.tsx`

- State: `sportFilter`, `leagueFilter`
- Fetch: `/api/history/chart?range=&sport=&league=`
- Sport pills: All, Baseball, Basketball, **WNBA**, Football, **Golf**, Hockey, **Soccer**
- Use API `buckets[].label` when present

### D. WNBA / PGA / Soccer scanning

In the **production** scan loop (monitor + `/api/opportunities`), ensure Optic Odds fetches include:

| Sport | Leagues |
|-------|---------|
| basketball | `nba`, **`wnba`** |
| golf | **`pga`** |
| soccer | **`mls`**, **`epl`**, **`uefa_champs_league`** |

Store `league` on `arb_history` rows for History filters.

Do **not** remove Kalshi/Polymarket legs from opportunity detection.

## Step 3 — Verify after Publish

```bash
curl https://arbitrage-sports-bot.replit.app/api/config
# No oddsjamApiKey

curl "https://arbitrage-sports-bot.replit.app/api/history/chart?range=today" | jq '.buckets | length'
# 24

curl "https://arbitrage-sports-bot.replit.app/api/opportunities" | jq '[.[].legs[].bookmaker] | unique'
# Should still include kalshi (and polymarket when present)
```

## What Cursor can do next

Once Replit is **pushed to GitHub**, say **“production is on GitHub branch X”** and we will implement patches on that branch without replacing your architecture.
