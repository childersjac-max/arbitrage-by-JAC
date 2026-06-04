# Step-by-step: add multi-agent LLM to your computer (standalone)

This folder is **not** part of arbitrage-by-JAC. Put it anywhere, e.g. `C:\Users\child\Projects\multi-agent-llm`.

---

## Step 1 — Copy the folder

Copy the entire `multi-agent-llm` directory to:

```text
C:\Users\child\Projects\multi-agent-llm
```

Required files inside:

- `multi_agent_runner.py`
- `requirements.txt`
- `.env.example`
- `setup.sh`, `run.sh`, `activate_venv.sh`

---

## Step 2 — Install Ollama

1. Download: https://ollama.com  
2. Install and open **Ollama** (whale icon in tray).  
3. Git Bash test:

```bash
curl -s http://127.0.0.1:11434/api/tags
```

---

## Step 3 — Create config

```bash
cd ~/Projects/multi-agent-llm
cp .env.example .env
```

Edit `.env` if you want a different task:

```env
MULTI_AGENT_TASK=Write a Python function to validate email addresses
```

---

## Step 4 — Pull AI models

```bash
ollama pull qwen2.5-coder:7b-instruct-q4_K_M
ollama pull qwen2.5:3b-instruct-q4_K_M
ollama list
```

**Note:** The sample used `qwen2.5:14b` for Model B — that is too large for 16 GB RAM. This project uses **3B** for the reviewer instead.

---

## Step 5 — Python virtual environment

```bash
cd ~/Projects/multi-agent-llm
py -3.14 -m venv .venv
source .venv/Scripts/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

---

## Step 6 — Run multi-agent loop

Default task (email validator):

```bash
source ./activate_venv.sh
python multi_agent_runner.py
```

Custom task:

```bash
python multi_agent_runner.py "Write a CLI that renames files by date"
```

You will see:

- `[THOUGHT]` — what step is running  
- Streaming text from Model A and Model B  
- `Score: X/10` each round  
- Final **BEST SOLUTION FOUND**

---

## Step 7 — Every day after

```bash
cd ~/Projects/multi-agent-llm
# Ollama running in tray
source ./activate_venv.sh
python multi_agent_runner.py "Your task here"
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Connection refused | Start Ollama |
| Model not found | `ollama pull <name from .env>` |
| Very slow | Normal for 7B on CPU; use shorter task or only Model B as 1.5B |
| `python` not found | Use `py -3.14` and `source .venv/Scripts/activate` |

---

## What the code does (novice)

1. **`ask()`** — sends prompt to Ollama, prints live tokens.  
2. **Model A** — writes code.  
3. **Model B** — reviews with Bugs / Improvements / Revised Code / Score.  
4. **Loop** — up to 3 times until score is high or no bugs.  
5. **Print** — best solution at the end.

All logic is in **`multi_agent_runner.py`** — open it in an editor to read the comments.
