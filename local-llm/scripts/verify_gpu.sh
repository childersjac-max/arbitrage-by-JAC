#!/usr/bin/env bash
# Verify GPU acceleration and local inference endpoint latency.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

OLLAMA_HOST="${OLLAMA_HOST:-http://127.0.0.1:11434}"
VLLM_BASE_URL="${VLLM_BASE_URL:-http://127.0.0.1:8000}"

echo "========== Hardware =========="
if command -v nvidia-smi &>/dev/null; then
  echo "--- NVIDIA (CUDA) ---"
  nvidia-smi --query-gpu=name,driver_version,memory.total,utilization.gpu --format=csv
else
  echo "nvidia-smi not found (skip if on Apple Silicon using Metal via native Ollama)."
fi

if [[ "$(uname -s)" == "Darwin" ]]; then
  echo "--- Apple Silicon ---"
  system_profiler SPHardwareDataType 2>/dev/null | grep -E "Chip|Memory" || true
  if command -v ollama &>/dev/null; then
    echo "Use native Ollama.app for Metal acceleration (recommended on macOS)."
  fi
fi

echo ""
echo "========== Ollama =========="
if curl -sf "${OLLAMA_HOST}/api/tags" >/dev/null 2>&1; then
  echo "Ollama reachable at ${OLLAMA_HOST}"
  curl -s "${OLLAMA_HOST}/api/tags" | head -c 2000
  echo ""
  if command -v ollama &>/dev/null; then
    echo "--- ollama ps (loaded models / processor) ---"
    ollama ps 2>/dev/null || docker exec local-llm-ollama ollama ps 2>/dev/null || true
  fi
  echo "--- Quick inference probe (watch GPU util during this) ---"
  MODEL="${OLLAMA_MODEL:-llama3.1:8b-instruct-q4_K_M}"
  START=$(date +%s%N)
  curl -sf "${OLLAMA_HOST}/api/generate" -d "{\"model\":\"${MODEL}\",\"prompt\":\"Say OK\",\"stream\":false,\"options\":{\"num_predict\":8}}" \
    | head -c 500
  END=$(date +%s%N)
  MS=$(( (END - START) / 1000000 ))
  echo ""
  echo "Generate round-trip: ${MS} ms (lower is better; compare with ollama ps showing GPU/Metal)"
else
  echo "Ollama not reachable at ${OLLAMA_HOST}"
fi

echo ""
echo "========== vLLM =========="
if curl -sf "${VLLM_BASE_URL}/health" >/dev/null 2>&1; then
  echo "vLLM health OK at ${VLLM_BASE_URL}"
  curl -sf "${VLLM_BASE_URL}/v1/models" | head -c 1000
  echo ""
else
  echo "vLLM not reachable at ${VLLM_BASE_URL} (optional)"
fi

echo ""
echo "========== Python client health =========="
if [[ -f .venv/bin/activate ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi
python - <<'PY' || true
import asyncio
import sys
sys.path.insert(0, ".")
from local_inference import LocalInferenceClient

async def main():
    async with LocalInferenceClient() as c:
        h = await c.health_check()
        print("health_check:", h)

asyncio.run(main())
PY
