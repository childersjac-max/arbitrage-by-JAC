#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -r requirements-app.txt
export LOCAL_LLM_UI_LAN=1
echo "Starting chat for phone access (same Wi-Fi)..."
echo "Look for a URL like http://192.168.x.x:7860 in the output."
python web_app.py
