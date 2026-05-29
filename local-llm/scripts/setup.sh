#!/usr/bin/env bash
# Spin up local LLM stack for entity normalization.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

BACKEND="${1:-ollama}"
PYTHON="${PYTHON:-python3}"

echo "==> Local LLM setup (backend=$BACKEND)"

if [[ ! -d .venv ]]; then
  "$PYTHON" -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example — edit OLLAMA_MODEL / VLLM_MODEL for your GPU RAM."
fi

case "$BACKEND" in
  ollama)
    if command -v docker &>/dev/null; then
      echo "==> Starting Ollama via Docker Compose (NVIDIA profile)..."
      docker compose --profile ollama up -d
      echo "Waiting for Ollama health..."
      sleep 5
      if docker compose --profile ollama ps | grep -q healthy; then
        echo "Ollama container healthy."
      fi
      echo "==> Pulling models (this may take a while)..."
      docker exec local-llm-ollama ollama pull "${OLLAMA_MODEL:-llama3.1:8b-instruct-q4_K_M}" || true
      docker exec local-llm-ollama ollama pull llama3.3:70b-instruct-q4_K_M 2>/dev/null || true
    else
      echo "Docker not found. Install Ollama natively: https://ollama.com/download"
      if command -v ollama &>/dev/null; then
        ollama serve &
        sleep 2
        ollama pull llama3.1:8b-instruct-q4_K_M
      fi
    fi
    ;;
  vllm)
    if ! command -v docker &>/dev/null; then
      echo "vLLM profile requires Docker + NVIDIA GPU." >&2
      exit 1
    fi
    echo "==> Starting vLLM OpenAI server..."
    docker compose --profile vllm up -d
  echo "Set LOCAL_LLM_BACKEND=vllm in .env"
    ;;
  *)
    echo "Usage: $0 [ollama|vllm]" >&2
    exit 1
    ;;
esac

echo ""
echo "Setup complete. Next:"
echo "  source .venv/bin/activate"
echo "  ./scripts/verify_gpu.sh"
echo "  python examples/normalize_batch.py"
