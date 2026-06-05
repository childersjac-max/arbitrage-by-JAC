# AutoGen + Ollama (fix for your `~/agent.py` error)

## What went wrong

| Issue | Your script | Fix |
|--------|-------------|-----|
| Model | `llama3.1` | Use a model you **pulled**: `qwen2.5:3b-instruct-q4_K_M` |
| Hang / CancelledError | Ollama waiting on missing/slow model | `ollama pull ...` + smaller model |
| `KeyboardInterrupt` | You pressed Ctrl+C while waiting | Normal on CPU; wait or use 3B |
| Global Python 3.14 | Packages in user site-packages | Use **venv** in `multi-agent-llm` |

AutoGen **is** using your local LLM (Ollama). It is **not** the Gradio chat at `:7860` — different apps, same Ollama backend.

---

## Setup (Git Bash)

```bash
cd ~/Projects/multi-agent-llm

# Ollama running
ollama pull qwen2.5:3b-instruct-q4_K_M
curl -s http://127.0.0.1:11434/api/tags

py -3.14 -m venv .venv
source .venv/Scripts/activate
python -m pip install -r requirements-autogen.txt

cp .env.example .env
```

Add to `.env`:

```env
AUTOGEN_MODEL=qwen2.5:3b-instruct-q4_K_M
OLLAMA_HOST=http://127.0.0.1:11434
AUTOGEN_RUN_CODE=0
AUTOGEN_NUM_PREDICT=512
```

---

## Run (chat only — start here)

```bash
cd ~/Projects/multi-agent-llm
source ./activate_venv.sh
python autogen_agent.py "Write a Python script that sorts a list of numbers"
```

Interactive:

```bash
python autogen_agent.py --interactive
```

---

## Run with code execution (advanced)

```env
AUTOGEN_RUN_CODE=1
```

```bash
python autogen_agent.py "Write and run a Python script that sorts [3,1,2]"
```

Output files land in `multi-agent-llm/autogen_workspace/`.

---

## Replace your broken `~/agent.py`

Either delete `~/agent.py` and use `multi-agent-llm/autogen_agent.py`, or fix home script:

```python
model_client = OllamaChatCompletionClient(
    model="qwen2.5:3b-instruct-q4_K_M",
    host="http://127.0.0.1:11434",
    model_info={
        "vision": False,
        "function_calling": True,
        "json_output": False,
        "family": "qwen2.5",
        "structured_output": False,
    },
    num_predict=512,
)
```

---

## Which tool when?

| Tool | Command | Use |
|------|---------|-----|
| **3-agent runner** | `python multi_agent_runner.py "..."` | Planner+coder+reviewer, no AutoGen |
| **AutoGen** | `python autogen_agent.py "..."` | Multi-agent chat + optional code run |
| **Gradio chat** | `arbitrage-by-JAC/local-llm/web_app.py` | Browser UI :7860 |

All share **one Ollama** — don't run huge jobs in parallel.
