#!/usr/bin/env bash
# Windows Git Bash: bash setup.sh
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [[ ! -f ../harvester/arbitrage_orchestrator.py ]]; then
  echo "ERROR: ../harvester/ not found."
  echo "Clone the FULL repo, then run setup from sports_arbitrage_pipeline/:"
  echo "  git clone https://github.com/childersjac-max/arbitrage-by-JAC.git"
  echo "  cd arbitrage-by-JAC/sports_arbitrage_pipeline"
  echo "  bash setup.sh"
  exit 1
fi

python -m venv venv
# shellcheck disable=SC1091
source venv/Scripts/activate 2>/dev/null || source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

mkdir -p ../harvester/data
if [[ ! -f ../harvester/.env ]] && [[ -f .env.example ]]; then
  cp .env.example ../harvester/.env
  echo "Created ../harvester/.env — edit ODDS_API_KEY"
fi

echo ""
echo "Ollama (optional for chat/normalize):"
echo "  ollama pull qwen2.5:3b-instruct-q4_K_M"
echo ""
echo "Run pipeline:"
echo "  source venv/Scripts/activate"
echo "  python arbitrage_orchestrator.py"
echo ""
