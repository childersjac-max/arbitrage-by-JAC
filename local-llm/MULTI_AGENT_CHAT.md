# Multi-agent flow in the browser chat

The Gradio UI (`web_app.py`) can run the same **Planner → Coder → Reviewer** pipeline as `multi-agent-llm/multi_agent_runner.py`.

## Requirements

1. **Ollama** running (system tray).
2. Repo layout (both folders side by side):

```text
arbitrage-by-JAC/
  local-llm/
  multi-agent-llm/
```

3. Models pulled:

```bash
ollama pull qwen2.5:3b-instruct-q4_K_M
ollama pull qwen2.5-coder:7b-instruct-q4_K_M
```

## Run

```bash
cd local-llm
source .venv/Scripts/activate   # Git Bash on Windows
python web_app.py
```

Open **http://127.0.0.1:7860**

1. On the **Chat** tab, set **Chat mode** → **Multi-agent (Planner → Coder → Reviewer)**.
2. Type your task and click **Send**.
3. Watch `[THOUGHT]` lines and streaming output in the chat bubble.
4. The final **BEST SOLUTION** block is at the bottom of the reply.

## Configure models

Edit `multi-agent-llm/.env` (copy from `.env.example`):

```env
MODEL_PLANNER=qwen2.5:3b-instruct-q4_K_M
MODEL_CODER=qwen2.5-coder:7b-instruct-q4_K_M
MODEL_REVIEWER=qwen2.5:3b-instruct-q4_K_M
MAX_LOOPS=3
DELAY_BETWEEN_CALLS=2
```

On 16GB RAM / CPU, set `MODEL_CODER` to the 3B tag for faster runs.

## Troubleshooting

| Error | Fix |
|-------|-----|
| `No module named 'pipeline_core'` | `ls multi-agent-llm/pipeline_core.py` — if missing: `git checkout cursor/gradio-multi-agent-4fea -- multi-agent-llm` then restart `web_app.py` |
| Multi-agent folder not found | Run `web_app.py` from repo with **both** `local-llm/` and `multi-agent-llm/` siblings |

## Notes

- Multi-agent turns take **several minutes** on CPU (7B coder step).
- Only **one** Ollama job runs at a time (chat, architect, and multi-agent share a lock).
- Switch back to **Single chat** for quick Q&A with the performance profile models.
