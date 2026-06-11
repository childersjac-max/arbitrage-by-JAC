#!/usr/bin/env bash
# Unattended multi-agent — all deploy phases (no Gradio copy-paste)
set -euo pipefail
cd "$(dirname "$0")"
if [[ -f .venv/Scripts/activate ]]; then
  # shellcheck disable=SC1091
  source .venv/Scripts/activate
elif [[ -f .venv/bin/activate ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi
export INJECT_FILE_MAP="${INJECT_FILE_MAP:-0}"
python run_phases.py "$@"
