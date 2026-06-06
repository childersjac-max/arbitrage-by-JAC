# Run Odds API + harvester with your Local LLM

Your local LLM should **guide commands**, not invent new code. Use one of the prompts below.

## Prompt files (copy entire file into chat)

| File | Best for |
|------|----------|
| `prompts/llm_operator_odds_api_harvester.txt` | Full step-by-step operator (recommended) |
| `prompts/llm_operator_odds_api_harvester_SHORT.txt` | Multi-agent / token limits |

Paths from repo root:

```text
~/Projects/arbitrage-by-JAC/prompts/llm_operator_odds_api_harvester.txt
```

## How to run the prompt

### A — Browser multi-agent (Gradio)

```bash
cd ~/Projects/arbitrage-by-JAC/local-llm
source .venv/Scripts/activate
python web_app.py
```

1. Chat mode → **Multi-agent**
2. Paste contents of `prompts/llm_operator_odds_api_harvester_SHORT.txt`
3. Follow one command at a time; paste terminal output back into chat

### B — Terminal multi-agent

```bash
cd ~/Projects/arbitrage-by-JAC/multi-agent-llm
source .venv/Scripts/activate
python multi_agent_runner.py --interactive
```

Paste the SHORT prompt when asked for a task.

### C — Single chat (faster)

Gradio → **Single chat** → **Balanced** profile → paste SHORT prompt.

## What you need before starting

1. **Odds API key** — https://the-odds-api.com/
2. **Repo** with `harvester/` and `sports_arbitrage_pipeline/`
3. **Git Bash** on Windows

## What the LLM will NOT do

- Create `stealth_session.py` or scrape bookmaker sites
- Replace the harvester with a greenfield project
- Run commands on your PC (you paste output back)

## Manual run (no LLM)

```bash
cd ~/Projects/arbitrage-by-JAC/sports_arbitrage_pipeline
source venv/Scripts/activate
cp ../sports_arbitrage_pipeline/.env.example ../harvester/.env
# Edit harvester/.env → ODDS_API_KEY=...
python arbitrage_orchestrator.py --sport basketball_nba
```
