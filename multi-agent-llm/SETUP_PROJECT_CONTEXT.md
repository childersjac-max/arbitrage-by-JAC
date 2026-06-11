# Multi-agent always knows: sports arbitrage project + file map + app URLs

## What this does

Every **Planner / Coder / Reviewer** call automatically receives:

1. `prompts/PROJECT_CONTEXT.txt` — project identity, rules, default commands  
2. `prompts/PROJECT_FILE_MAP.txt` — all real file paths (optional, on by default)  
3. Your **app URLs** from `.env`

Works in:

- `multi_agent_runner.py` (terminal)
- `local-llm/web_app.py` → Chat mode → **Multi-agent**

---

## One-time setup (your PC)

### Step 1 — Pull latest

```bash
cd ~/Projects/arbitrage-by-JAC
git fetch origin cursor/multi-agent-project-context-4fea
git checkout cursor/multi-agent-project-context-4fea
# or merge into your working branch
```

### Step 2 — Configure multi-agent `.env`

```bash
cd ~/Projects/arbitrage-by-JAC/multi-agent-llm
cp .env.example .env
notepad .env
```

Set your paths and URLs:

```env
PROJECT_ROOT=C:/Users/child/Projects/arbitrage-by-JAC
PROJECT_ROOT_BASH=~/Projects/arbitrage-by-JAC

# Find LAN IP: ipconfig | findstr IPv4
LAN_IP=192.168.1.XXX
APP_URL_LOCAL_LLM=http://127.0.0.1:7860
APP_URL_LOCAL_LLM_LAN=http://192.168.1.XXX:7860
APP_URL_HARVESTER=http://127.0.0.1:8765

INJECT_PROJECT_CONTEXT=1
INJECT_FILE_MAP=1
```

### Step 3 — Configure local-llm `.env` (browser app URL)

```bash
cd ~/Projects/arbitrage-by-JAC/local-llm
cp .env.example .env
```

Add to `local-llm/.env`:

```env
LOCAL_LLM_UI_HOST=127.0.0.1
LOCAL_LLM_UI_PORT=7860
LOCAL_LLM_UI_LAN=1
PROJECT_ROOT=C:/Users/child/Projects/arbitrage-by-JAC
APP_URL_HARVESTER=http://127.0.0.1:8765
INJECT_PROJECT_CONTEXT_IN_CHAT=1
```

### Step 4 — Phone URL (same Wi-Fi)

```bash
cd ~/Projects/arbitrage-by-JAC/local-llm
source .venv/Scripts/activate
python web_app.py
```

Startup banner prints **phone URLs** like `http://192.168.x.x:7860`.  
Copy that into `multi-agent-llm/.env` → `APP_URL_LOCAL_LLM_LAN`.

### Step 5 — Public URL (optional, Gradio share)

In `local-llm/.env`:

```env
LOCAL_LLM_UI_SHARE=1
```

Restart `web_app.py` — Gradio prints a `https://....gradio.live` URL.  
Save it as `APP_URL_PUBLIC` in `multi-agent-llm/.env`.

### Step 6 — Test context injection

```bash
cd ~/Projects/arbitrage-by-JAC/multi-agent-llm
source .venv/Scripts/activate
python -c "from project_context import project_context_block; print(project_context_block()[:800])"
```

You should see sports arbitrage project name and file paths.

### Step 7 — Run multi-agent

**Browser:**

```bash
cd ~/Projects/arbitrage-by-JAC/local-llm
python web_app.py
```

Open **APP_URL_LOCAL_LLM** → Multi-agent mode → ask:  
`What file runs the Odds API orchestrator?`

**Terminal:**

```bash
cd ~/Projects/arbitrage-by-JAC/multi-agent-llm
python multi_agent_runner.py "Add a comment to harvester/arbitrage_orchestrator.py explaining the output path"
```

---

## Customize context

| File | Purpose |
|------|---------|
| `prompts/PROJECT_CONTEXT.txt` | Global rules (repo root) |
| `prompts/PROJECT_FILE_MAP.txt` | All paths |
| `multi-agent-llm/prompts/project_context.txt` | Override (optional) |

Disable injection: `INJECT_PROJECT_CONTEXT=0` in `multi-agent-llm/.env`

---

## App URL summary

| App | Default URL | Env var |
|-----|-------------|---------|
| Local LLM + multi-agent | http://127.0.0.1:7860 | APP_URL_LOCAL_LLM |
| Phone on Wi-Fi | http://LAN_IP:7860 | APP_URL_LOCAL_LLM_LAN |
| Harvester dashboard | http://127.0.0.1:8765 | APP_URL_HARVESTER |
| Public Gradio share | https://....gradio.live | APP_URL_PUBLIC |
