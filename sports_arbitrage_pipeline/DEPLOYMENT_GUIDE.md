# Deployment guide (Windows + Git Bash) — corrected

Use this instead of a generic LLM checklist that omits file paths.

## 1. Get the full repository

```bash
cd ~/Projects
git clone https://github.com/childersjac-max/arbitrage-by-JAC.git
cd arbitrage-by-JAC/sports_arbitrage_pipeline
```

## 2. Python venv

```bash
python -m venv venv
source venv/Scripts/activate    # Windows Git Bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 3. API key (required)

```bash
cp .env.example ../harvester/.env
# Edit ../harvester/.env — set ODDS_API_KEY=...
```

## 4. Ollama (optional)

```bash
ollama pull qwen2.5:3b-instruct-q4_K_M
curl -s http://127.0.0.1:11434/api/tags
```

## 5. Playwright

**Skip** for the lawful orchestrator (uses The Odds API over HTTP).  
If needed elsewhere: `pip install playwright` then `python -m playwright install chromium`.

## 6. Run

```bash
source venv/Scripts/activate
python arbitrage_orchestrator.py
```

## Troubleshooting

| Error | Fix |
|--------|-----|
| `can't open file ... arbitrage_orchestrator.py` | Run from `sports_arbitrage_pipeline/` inside cloned repo, not an empty `~/sports_arbitrage_pipeline` |
| `harvester not found` | `export HARVESTER_ROOT=~/Projects/arbitrage-by-JAC/harvester` |
| No odds / 401 | Set `ODDS_API_KEY` in `harvester/.env` |
