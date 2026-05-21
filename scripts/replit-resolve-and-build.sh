#!/bin/bash
# Run on Replit Shell (works during an in-progress merge; no git pull required):
#   curl -sL https://raw.githubusercontent.com/childersjac-max/arbitrage-by-JAC/main/scripts/replit-resolve-and-build.sh | bash
set -euo pipefail

cd "${REPL_HOME:-$HOME}/workspace" 2>/dev/null || cd ~/workspace || cd /home/runner/workspace

echo "==> workspace: $(pwd)"

if [ -f .git/MERGE_HEAD ]; then
  echo "==> resolving .replit merge conflict (use GitHub / origin version)"
  git checkout --theirs .replit
  git add .replit
  git commit -m "fix: resolve .replit merge — Node-only for Nix build" --no-edit
elif grep -q '^<<<<<<< ' .replit 2>/dev/null; then
  echo "==> conflict markers in .replit — resetting from origin/main"
  git fetch origin main
  git checkout origin/main -- .replit
  git add .replit
  git commit -m "fix: reset .replit from origin/main" || true
fi

if [ -f replit.nix ]; then
  echo "==> removing replit.nix (often breaks Nix after merge)"
  rm -f replit.nix
  git rm -f replit.nix 2>/dev/null || true
fi

echo "==> pnpm install"
pnpm install

echo "==> build api-server"
pnpm --filter @workspace/api-server run build

echo "==> build arb-finder"
pnpm --filter @workspace/arb-finder run build

echo ""
echo "SUCCESS. In Replit: Deploy → Publish, then hard-refresh /history"
echo "Verify: curl -s https://arbitrage-sports-bot.replit.app/api/history/chart?range=today | head -c 200"
