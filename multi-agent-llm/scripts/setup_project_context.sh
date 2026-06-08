#!/usr/bin/env bash
# One-time: wire sports-arbitrage project context + app URLs into multi-agent .env
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$(cd .. && pwd)"
MA_DIR="$(pwd)"

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created multi-agent-llm/.env"
fi

URL_FILE="$ROOT/local-llm/data/app_urls.txt"
if [[ -f "$URL_FILE" ]]; then
  echo "Merging URLs from $URL_FILE"
  while IFS= read -r line; do
    [[ "$line" =~ ^[A-Z_]+= ]] || continue
    key="${line%%=*}"
    val="${line#*=}"
    if grep -q "^${key}=" .env 2>/dev/null; then
      sed -i "s|^${key}=.*|${line}|" .env 2>/dev/null || true
    else
      echo "$line" >> .env
    fi
  done < "$URL_FILE"
else
  echo "Tip: run local-llm/web_app.py once to generate local-llm/data/app_urls.txt"
fi

grep -q '^PROJECT_ROOT=' .env || echo "PROJECT_ROOT=$ROOT" >> .env
grep -q '^PROJECT_ROOT_BASH=' .env || echo "PROJECT_ROOT_BASH=~/Projects/arbitrage-by-JAC" >> .env
grep -q '^INJECT_PROJECT_CONTEXT=' .env || echo "INJECT_PROJECT_CONTEXT=1" >> .env

echo "Done. Test:"
echo "  python -c \"from project_context import project_context_block; print(project_context_block()[:400])\""
