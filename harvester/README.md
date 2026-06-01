# Harvester

Merged, runnable package layout for the arbitrage pipeline (from Architect phase plans).

## Layout

```text
harvester/
  config.py              # ODDS_API_* and pipeline settings
  models.py              # UnifiedRecord, SourceQuote, ArbitrageInfo
  engine.py              # fetch → normalize → arb detection
  cli.py                 # Command-line entry
  integrators/
    base.py              # OddsIntegrator ABC
    odds_api.py          # The Odds API v4 (live)
    stubs.py             # 14 platform stubs (lawful TODOs)
  normalization/
    bridge.py            # Calls ../local-llm normalize_batch
  generated/             # Architect output archives (timestamp folders)
  scripts/
    run_pipeline.bat     # Windows helper
    promote_generated.py # Extract code from generated/ for comparison
```

## Setup (Windows / Git Bash)

```bash
cd /c/Users/child/Projects/arbitrage-by-JAC/harvester
cp .env.example .env
# Edit .env — set ODDS_API_KEY

python -m venv .venv
source .venv/Scripts/activate   # Git Bash on Windows
pip install -r requirements.txt
```

Ensure **Ollama** is running if `HARVESTER_USE_LOCAL_NORMALIZATION=true` (uses `local-llm/`).

## Commands

```bash
# Health check
python cli.py health

# Fetch NBA h2h, normalize names, print JSON
python cli.py run

# Only rows with arbitrage above threshold
python cli.py run --arbs-only -o output.json

# List stub platforms
python cli.py list-stubs
```

From repo root:

```bash
python -m harvester health
```

## Architect output vs this package

| Location | Purpose |
|----------|---------|
| `harvester/generated/<timestamp>/` | Raw Architect run (plan.json, phase_*.md) |
| `harvester/` (this tree) | **Canonical** merged implementation |
| `harvester/_promoted/<timestamp>/` | Optional extract of phase markdown (reference) |

To compare your LLM phases to this package:

```bash
python scripts/promote_generated.py
# Review harvester/_promoted/<newest>/
```

## Unified record shape

```json
{
  "timestamp": "2026-05-29T12:00:00Z",
  "normalized_event_name": "Lakers @ Celtics",
  "market_type": "h2h",
  "sources": { "draftkings": [{ "outcome": "...", "price": 2.1 }] },
  "arbitrage": { "yield_pct": 1.2, "legs": [] }
}
```

## Next steps

1. Set `ODDS_API_KEY` and run `python cli.py health`.
2. Run `python cli.py run --arbs-only` and inspect JSON.
3. Implement a stub integrator when you have a lawful API (see `list-stubs`).
