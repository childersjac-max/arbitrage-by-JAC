# Sports arbitrage pipeline (Windows / Git Bash entry)

This folder is the **novice-friendly entry point** for the lawful harvester in `../harvester/`.

Your local LLM guide assumed `arbitrage_orchestrator.py` lives here — it does **after** you use the full repo layout below.

## One-time setup (correct way)

Do **not** only `mkdir sports_arbitrage_pipeline` in your home folder. Clone the **full** repository:

```bash
cd ~/Projects
git clone https://github.com/childersjac-max/arbitrage-by-JAC.git
cd arbitrage-by-JAC/sports_arbitrage_pipeline
bash setup.sh
```

**Windows Git Bash** — same paths; `setup.sh` uses `venv/Scripts/activate`.

Edit API key:

```bash
# File used by the orchestrator:
nano ../harvester/.env
# Set: ODDS_API_KEY=your_key_from_the-odds-api.com
```

## Run the orchestrator

```bash
cd ~/Projects/arbitrage-by-JAC/sports_arbitrage_pipeline
source venv/Scripts/activate
python arbitrage_orchestrator.py
```

With options:

```bash
python arbitrage_orchestrator.py --sport basketball_nba --markets h2h spreads totals
```

Output: `harvester/data/ingestion_snapshot.json`

## Ollama (optional — for local-llm chat, not required to run orchestrator)

```bash
ollama pull qwen2.5:3b-instruct-q4_K_M
curl -s http://127.0.0.1:11434/api/tags
```

## Playwright — **not required** for this orchestrator

The lawful pipeline uses **The Odds API** (HTTP), not browser scraping. Skip `playwright install` unless you build separate browser tools.

If you still need Playwright elsewhere:

```bash
pip install playwright
python -m playwright install chromium
```

## If you already have `~/sports_arbitrage_pipeline` (empty/wrong)

**Option A — recommended:** move aside and clone:

```bash
mv ~/sports_arbitrage_pipeline ~/sports_arbitrage_pipeline.old
git clone https://github.com/childersjac-max/arbitrage-by-JAC.git ~/Projects/arbitrage-by-JAC
cd ~/Projects/arbitrage-by-JAC/sports_arbitrage_pipeline
bash setup.sh
```

**Option B — keep folder, point at harvester:**

```bash
export HARVESTER_ROOT=~/Projects/arbitrage-by-JAC/harvester
cd ~/sports_arbitrage_pipeline
# Copy arbitrage_orchestrator.py + harvester_launcher.py from the repo into this folder
pip install -r requirements.txt
python arbitrage_orchestrator.py
```

## Environment variables

| Variable | Required | Notes |
|----------|----------|--------|
| `ODDS_API_KEY` | **Yes** | In `harvester/.env` |
| `THE_ODDS_API_KEY` | Alias | Also accepted |
| `HARVESTER_ROOT` | No | Path to `harvester/` if auto-detect fails |

## Verify

```bash
cd ../harvester
python cli.py health
```

## Dashboard (optional)

```bash
cd ../harvester
python web_app.py
# http://127.0.0.1:8765
```

See `../harvester/docs/LAWFUL_PIPELINE.md` for what “14 books” means (API vs direct integrations).
