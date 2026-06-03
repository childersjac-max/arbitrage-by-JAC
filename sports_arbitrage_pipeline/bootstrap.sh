#!/usr/bin/env bash
# One-shot setup: venv + deps + harvester code (clones repo if needed)
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [[ "$(basename "$ROOT")" == "sports_arbitrage_pipeline" && "$(basename "$(dirname "$ROOT")")" == "sports_arbitrage_pipeline" ]]; then
  echo "WARNING: You are in a nested sports_arbitrage_pipeline/sports_arbitrage_pipeline folder."
  echo "  Recommended: cd ~/sports_arbitrage_pipeline   (one level up)"
  echo "  Or continue — bootstrap will still try to find harvester."
  echo ""
fi

find_harvester() {
  local d
  for d in \
    "$ROOT/harvester" \
    "$ROOT/../harvester" \
    "$ROOT/../../harvester" \
    "$ROOT/../arbitrage-by-JAC/harvester" \
    "$HOME/Projects/arbitrage-by-JAC/harvester" \
    "$HOME/arbitrage-by-JAC/harvester"; do
    if [[ -f "$d/arbitrage_orchestrator.py" ]]; then
      echo "$d"
      return 0
    fi
  done
  return 1
}

HARVESTER_DIR=""
if HARVESTER_DIR="$(find_harvester)"; then
  echo "Found harvester: $HARVESTER_DIR"
else
  echo "harvester/ not found — cloning arbitrage-by-JAC next to this folder..."
  CLONE_TARGET="$ROOT/../arbitrage-by-JAC"
  if [[ ! -d "$CLONE_TARGET/.git" ]]; then
    git clone https://github.com/childersjac-max/arbitrage-by-JAC.git "$CLONE_TARGET"
  fi
  HARVESTER_DIR="$CLONE_TARGET/harvester"
  if [[ ! -f "$HARVESTER_DIR/arbitrage_orchestrator.py" ]]; then
    echo "ERROR: clone succeeded but harvester/ is missing."
    exit 1
  fi
fi

echo "HARVESTER_ROOT=$HARVESTER_DIR" > "$ROOT/local.env"
echo "Wrote $ROOT/local.env"

if [[ ! -d "$ROOT/venv" ]]; then
  python -m venv venv
fi
# shellcheck disable=SC1091
source "$ROOT/venv/Scripts/activate" 2>/dev/null || source "$ROOT/venv/bin/activate"
python -m pip install --upgrade pip
pip install -r requirements.txt

mkdir -p "$HARVESTER_DIR/data"
if [[ ! -f "$HARVESTER_DIR/.env" ]] && [[ -f "$ROOT/.env.example" ]]; then
  cp "$ROOT/.env.example" "$HARVESTER_DIR/.env"
  echo "Created $HARVESTER_DIR/.env — set ODDS_API_KEY"
fi

echo ""
echo "Optional — Playwright browsers (NOT required for orchestrator):"
echo "  bash install_playwright.sh"
echo ""
echo "Done. Every time you open Git Bash:"
echo "  cd \"$ROOT\""
echo "  source ./activate_venv.sh"
echo "  python arbitrage_orchestrator.py"
echo ""
