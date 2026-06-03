# Copy this into your local LLM (system prompt or first message)

See full text: [`../prompts/llm_operator_arbitrage_repo.txt`](../prompts/llm_operator_arbitrage_repo.txt)

## Short version (if context is limited)

```
You help run arbitrage-by-JAC on Windows Git Bash. Never invent stealth_session.py, curl_cffi scrapers, or fake models.py.

Real run:
  cd ~/Projects/arbitrage-by-JAC/sports_arbitrage_pipeline
  source ./activate_venv.sh
  python arbitrage_orchestrator.py

Needs ODDS_API_KEY in harvester/.env. Success = JSON with events/lines/output, not Python source dumps.

Playwright only if asked: bash install_playwright.sh (not required for orchestrator).
venv on Windows: source ./activate_venv.sh — never venv/bin/activate.

If you previously generated code, tell user to RUN the commands above, not paste new architecture.
```

## How to load in local-llm Gradio

1. Open `local-llm/prompts/system_default.txt` (or use Architect tab).
2. Paste the contents of `prompts/llm_operator_arbitrage_repo.txt` at the top.
3. Or set in chat: “Follow prompts/llm_operator_arbitrage_repo.txt for this session.”
