# Easiest way to run your big prompt

## Option A — No browser (recommended)

1. Open **Ollama** from the Start menu.
2. In File Explorer go to:
   `arbitrage-by-JAC\local-llm\scripts`
3. **Double-click:** `run_architect_easy.bat`
4. Notepad opens — paste or edit your prompt → **Save** → close Notepad.
5. Wait 5–15 minutes in the black window.
6. Open results:
   `arbitrage-by-JAC\harvester\generated\`  
   (newest dated folder → `README.txt`)

**Runnable package:** Architect phases are merged into `harvester/` (see `harvester/README.md`).  
Set `ODDS_API_KEY` in `harvester/.env`, then run `harvester\scripts\run_pipeline.bat run health`.

## Option B — Web app

1. Ollama open.
2. Git Bash:
   ```bash
   cd /c/Users/child/Projects/arbitrage-by-JAC/local-llm
   source .venv/Scripts/activate
   python web_app.py
   ```
3. Browser: http://127.0.0.1:7860 → tab **Architect (8B)**.
4. Click **START — Run my big prompt** (green).
5. Results auto-save to `harvester/generated/`.

## Edit your prompt anytime

File:
`local-llm\prompts\mega_prompt.txt`

Lines starting with `#` are notes for you only (ignored when running easy.bat).
