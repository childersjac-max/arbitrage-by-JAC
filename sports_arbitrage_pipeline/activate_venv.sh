#!/usr/bin/env bash
# Source this on Windows Git Bash OR Linux/macOS:
#   source ./activate_venv.sh
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
if [[ -f "$ROOT/venv/Scripts/activate" ]]; then
  # Windows (Git Bash, CMD venv)
  # shellcheck disable=SC1091
  source "$ROOT/venv/Scripts/activate"
elif [[ -f "$ROOT/venv/bin/activate" ]]; then
  # Linux / macOS
  # shellcheck disable=SC1091
  source "$ROOT/venv/bin/activate"
else
  echo "No venv found. Run first:"
  echo "  cd \"$ROOT\""
  echo "  bash setup.sh"
  return 1 2>/dev/null || exit 1
fi
echo "Activated: $ROOT/venv ($(python --version 2>&1))"
