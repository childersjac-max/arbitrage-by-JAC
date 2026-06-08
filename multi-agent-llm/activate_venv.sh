#!/usr/bin/env bash
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$ROOT/.venv/Scripts/activate" ]]; then
  # shellcheck disable=SC1091
  source "$ROOT/.venv/Scripts/activate"
elif [[ -f "$ROOT/.venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "$ROOT/.venv/bin/activate"
else
  echo "No venv. Run: bash setup.sh"
  return 1 2>/dev/null || exit 1
fi
echo "Activated: $(python --version 2>&1)"
