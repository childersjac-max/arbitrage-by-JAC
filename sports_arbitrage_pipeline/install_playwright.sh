#!/usr/bin/env bash
# Download Playwright browser binaries (Windows Git Bash + Linux/macOS)
# Usage:  bash install_playwright.sh
#         bash install_playwright.sh --all-browsers
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [[ ! -d "$ROOT/venv" ]]; then
  echo "No venv yet. Run:  bash bootstrap.sh"
  exit 1
fi

# shellcheck disable=SC1091
source "$ROOT/activate_venv.sh"

echo "Installing Playwright Python package..."
pip install -r requirements-playwright.txt

echo ""
echo "Downloading browser binaries (this may take a few minutes)..."
if [[ "${1:-}" == "--all-browsers" ]]; then
  python -m playwright install
else
  python -m playwright install chromium
fi

echo ""
echo "Done. Verify:"
python -m playwright --version
echo ""
echo "Note: The lawful arbitrage orchestrator does NOT need Playwright."
echo "      It uses The Odds API over HTTP. Playwright is only for separate browser tools."
