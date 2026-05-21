# Fix: "The nix environment failed to build" (Replit)

After merging GitHub `main` into the Repl, Publish can fail with a Nix build error. The live app at [arbitrage-sports-bot.replit.app](https://arbitrage-sports-bot.replit.app) stays on the **last successful** publish until this is fixed.

## Likely causes

1. **`python-3.11` in `.replit`** — the arbitrage app runs on Node only; dual Node+Python modules often break Nix on Replit.
2. **`[postMerge]` running `scripts/post-merge.sh`** — `pnpm --filter db push` used the wrong package name and can fail without `DATABASE_URL`, blocking environment setup.
3. **Bad `replit.nix` from merge** — only exists on the Repl, not always in GitHub.

## Fix on Replit (pick one path)

### Path A — Recover + pull (fastest)

1. Open [Arbitrage-Sports-Bot](https://replit.com/@childersjac/Arbitrage-Sports-Bot).
2. Click **Recover original configuration files** (under the Nix error).
3. In Shell:

```bash
git pull origin main
```

4. Confirm `.replit` has **only** `modules = ["nodejs-24"]` and **no** `[postMerge]` block.
5. If `replit.nix` exists and you still see Nix errors, delete it in the file tree (Replit will regenerate from `.replit`).

### Path B — Edit `.replit` by hand

In the Repl editor, set:

```toml
modules = ["nodejs-24"]
```

Remove the entire `[postMerge]` section if present.

## Verify build before Publish

```bash
pnpm install
pnpm --filter @workspace/api-server run build
pnpm --filter @workspace/arb-finder run build
```

Both must exit 0. Then **Publish** (not only Run).

## After Publish — verify live

```bash
curl -s https://arbitrage-sports-bot.replit.app/api/config
# Must NOT contain oddsjamApiKey

curl -s "https://arbitrage-sports-bot.replit.app/api/history/chart?range=today" | jq '.buckets | length, .sportFilters'
# Expect: 24 buckets and sportFilters array
```

Open `/history` — sport pills (WNBA, Golf, Soccer) and 24-hour Today chart.

## Security

Production still exposes the OddsJam key in `/api/config`. After deploy with the secure config route, **rotate `ODDSJAM_API_KEY`** in Replit Secrets.

## What Publish does vs GitHub

| Action | Effect |
|--------|--------|
| Push to GitHub | Updates the repo only |
| `git pull` in Repl | Updates Repl files |
| **Publish** | Builds and deploys Repl code to `*.replit.app` |

GitHub alone does not update the live URL.
