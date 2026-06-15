# Quick start — Windows Git Bash (copy-paste)

You are here because the LLM said `source venv/bin/activate` — **that fails on Windows**. Use the commands below exactly.

## If you are in `sports_arbitrage_pipeline/sports_arbitrage_pipeline` (nested)

Go up one level OR stay and run bootstrap from current folder:

```bash
cd ~/sports_arbitrage_pipeline/sports_arbitrage_pipeline
# OR better:
cd ~/sports_arbitrage_pipeline
```

## One-time setup

```bash
cd ~/sports_arbitrage_pipeline
bash bootstrap.sh
```

This will:

1. Create `venv/`
2. Install Python packages
3. Clone `arbitrage-by-JAC` (if `harvester/` is missing) into `../arbitrage-by-JAC`
4. Write `local.env` with `HARVESTER_ROOT=...`

## Every new terminal

```bash
cd ~/sports_arbitrage_pipeline
source ./activate_venv.sh
```

**Do not use** `source venv/bin/activate` on Windows.

## API key

Edit the harvester env file (path printed by bootstrap), e.g.:

```bash
nano ../arbitrage-by-JAC/harvester/.env
```

Set:

```text
ODDS_API_KEY=your_key_from_the-odds-api.com
```

## Run

```bash
python arbitrage_orchestrator.py
```

## Ollama (optional)

```bash
ollama pull qwen2.5:3b-instruct-q4_K_M
```

## Playwright

**Not required** for `arbitrage_orchestrator.py` (uses The Odds API, not a browser).

If your setup guide says `playwright install` and you get **command not found**:

```bash
cd ~/Projects/arbitrage-by-JAC/sports_arbitrage_pipeline
source ./activate_venv.sh
bash install_playwright.sh
```

Or manually:

```bash
pip install -r requirements-playwright.txt
python -m playwright install chromium
```

Do **not** use `playwright install` alone — on Windows use **`python -m playwright install`**.
