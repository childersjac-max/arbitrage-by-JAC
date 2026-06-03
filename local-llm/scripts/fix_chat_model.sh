#!/usr/bin/env bash
# Fix Quality/7B chat timeouts on CPU — switch to Balanced 3B
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
# shellcheck disable=SC1091
source .venv/Scripts/activate 2>/dev/null || source .venv/bin/activate
python scripts/set_profile.py balanced
echo ""
echo "Pull model: ollama pull qwen2.5:3b-instruct-q4_K_M"
echo "Restart: python web_app.py — select Balanced in the UI"
