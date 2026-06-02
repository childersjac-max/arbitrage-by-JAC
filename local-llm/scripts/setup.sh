#!/usr/bin/env bash
# One-time setup for local-llm (Git Bash / Linux / macOS)
set -euo pipefail
cd "$(dirname "$0")/.."
echo "Installing into: $(pwd)"

if [[ ! -d .venv ]]; then
  echo "Creating .venv ..."
  python -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/Scripts/activate 2>/dev/null || source .venv/bin/activate

python -m pip install --upgrade pip
pip install -r requirements.txt -r requirements-app.txt

echo ""
echo "Done. Start the chat app with:"
echo "  source .venv/Scripts/activate   # Git Bash on Windows"
echo "  python web_app.py"
echo "  → http://127.0.0.1:7860"
