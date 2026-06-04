#!/usr/bin/env bash
# One-time setup — Windows Git Bash or Linux
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

echo "=== Multi-agent LLM (standalone) setup ==="

if ! command -v ollama >/dev/null 2>&1; then
  echo "Install Ollama from https://ollama.com first, then re-run this script."
  exit 1
fi

if [[ ! -f .env ]] && [[ -f .env.example ]]; then
  cp .env.example .env
  echo "Created .env from .env.example"
fi

# shellcheck disable=SC1091
if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

MODEL_A="${MULTI_AGENT_MODEL_A:-qwen2.5-coder:7b-instruct-q4_K_M}"
MODEL_B="${MULTI_AGENT_MODEL_B:-qwen2.5:3b-instruct-q4_K_M}"

echo "Pulling models (may take a while)..."
ollama pull "$MODEL_A"
ollama pull "$MODEL_B"

if command -v py >/dev/null 2>&1; then
  PY=py -3.14
elif command -v python3 >/dev/null 2>&1; then
  PY=python3
else
  PY=python
fi

$PY -m venv .venv
source .venv/Scripts/activate 2>/dev/null || source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo ""
echo "Done. Run:  source ./activate_venv.sh && python multi_agent_runner.py"
echo "Or:       bash run.sh"
