# Multi-Agent Local LLM (standalone)

**Independent project** — does not use `arbitrage-by-JAC`, `harvester`, or `local-llm`.

Three Ollama agents:

```text
Planner (3B) → Coder (7B) → Reviewer (3B) → loop until score ≥ 9 or max rounds
```

| Role | Default model | Job |
|------|----------------|-----|
| **Planner** | `qwen2.5:3b-instruct-q4_K_M` | Task decomposition (steps, inputs, edge cases) |
| **Coder** | `qwen2.5-coder:7b-instruct-q4_K_M` | Implementation |
| **Reviewer** | `qwen2.5:3b-instruct-q4_K_M` | Critique, revised code, score / confidence |

CPU-safe: **`DELAY_BETWEEN_CALLS`** between steps, small models for planner/reviewer.

Live **`[THOUGHT]`** + optional streaming output.

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

Interactive prompt:

```bash
python multi_agent_runner.py --interactive
```

Or set `MULTI_AGENT_TASK` in `.env`.

**Smart stop:** score ≥ 9 or no bugs · **Re-plan** if score &lt; 6

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

## AutoGen (optional)

If you installed `autogen-agentchat` and hit errors with `~/agent.py`:

```bash
pip install -r requirements-autogen.txt
python autogen_agent.py "Your task"
```

See **[AUTOGEN_SETUP.md](AUTOGEN_SETUP.md)** — use `qwen2.5:3b-instruct-q4_K_M`, not `llama3.1`.

## Browser chat (Gradio)

The repo’s **`local-llm/web_app.py`** can run this same pipeline in the browser:

1. Ensure `multi-agent-llm/` sits next to `local-llm/` in the repo.
2. Start `python web_app.py` from `local-llm/`.
3. Chat tab → **Chat mode** → **Multi-agent (Planner → Coder → Reviewer)**.

See **`local-llm/MULTI_AGENT_CHAT.md`**.

## Not included

- No connection to sports arbitrage / Odds API  
- No `server.py` / llama.cpp — **Ollama only**
