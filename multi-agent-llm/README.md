# Multi-Agent Local LLM (standalone)

**Independent project** — does not use `arbitrage-by-JAC`, `harvester`, or `local-llm`.

Two Ollama models cooperate:

| Role | Default model | Job |
|------|----------------|-----|
| **Model A** | `qwen2.5-coder:7b-instruct-q4_K_M` | Writes code |
| **Model B** | `qwen2.5:3b-instruct-q4_K_M` | Reviews and scores |

Live **`[THOUGHT]`** lines explain each step for beginners.

---

## Install on your PC (from scratch)

### Step 1 — Copy this folder anywhere

Example:

```text
C:\Users\child\Projects\multi-agent-llm\
```

You can copy `multi-agent-llm` out of the arbitrage repo, or clone only this folder.

### Step 2 — Install Ollama

1. [https://ollama.com](https://ollama.com) → download → install  
2. Start **Ollama** (system tray)  
3. Test:

```bash
curl -s http://127.0.0.1:11434/api/tags
```

### Step 3 — One-time setup (Git Bash)

```bash
cd ~/Projects/multi-agent-llm
bash setup.sh
```

On Windows, if `setup.sh` fails on venv, use:

```bash
py -3.14 -m venv .venv
source .venv/Scripts/activate
python -m pip install -r requirements.txt
cp .env.example .env
ollama pull qwen2.5:3b-instruct-q4_K_M
ollama pull qwen2.5-coder:7b-instruct-q4_K_M
```

### Step 4 — Run

```bash
cd ~/Projects/multi-agent-llm
source ./activate_venv.sh
python multi_agent_runner.py
```

Custom task:

```bash
python multi_agent_runner.py "Write a FastAPI health check endpoint"
```

Or set `MULTI_AGENT_TASK` in `.env`.

---

## Hardware notes (16 GB RAM, Intel UHD)

- **Model A (7B)** is slow on CPU — expect several minutes per step.  
- **Model B (3B)** is used instead of `qwen2.5:14b` (14B will not fit comfortably).  
- Edit `.env` to change models.

---

## Files

| File | Purpose |
|------|---------|
| `multi_agent_runner.py` | Main script |
| `.env` | Your models and task (from `.env.example`) |
| `setup.sh` / `setup.bat` | One-time install |
| `run.sh` / `run.bat` | Run the loop |

---

## Not included

- No Gradio UI  
- No connection to sports arbitrage / Odds API  
- No `server.py` / llama.cpp — **Ollama only**
