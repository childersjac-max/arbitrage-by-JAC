#!/usr/bin/env bash
# Apply UI phases A-F dashboard code from branch and print restart commands.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
BRANCH="${UI_BRANCH:-cursor/ui-card-filters-autorun-4fea}"

cd "$REPO_ROOT"
echo "Fetching origin/$BRANCH ..."
git fetch origin "$BRANCH"

echo "Checking out dashboard UI files ..."
git checkout "origin/$BRANCH" -- \
  harvester/dashboard_service.py \
  harvester/static/index.html \
  harvester/static/styles.css \
  harvester/static/app.js

echo ""
echo "UI files updated. Restart the dashboard:"
echo "  cd sports_arbitrage_pipeline && source venv/Scripts/activate && python arbitrage_orchestrator.py --full"
echo "  cd harvester && source ../sports_arbitrage_pipeline/venv/Scripts/activate && python web_app.py"
echo "  Open http://127.0.0.1:8765 and hard-refresh (Ctrl+Shift+R)"
