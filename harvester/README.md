# Arbitrage Harvester

Modular Python data pipeline for a real-time arbitrage app. The paid baseline
source is **The Odds API only**. Other source files are either official/public
HTTP adapters or structured stubs that return `source_unavailable`.

## Architecture

```text
The Odds API (paid, documented)       Optional public APIs / stubs
              |                                  |
              v                                  v
   harvester/baseline/odds_api_client.py   harvester/adapters/*.py
              |                                  |
              +----------- SourceQuote ---------+
                              |
                              v
             harvester/normalize/bridge.py
        (cache + aliases + local-llm for fuzzy names only)
                              |
                              v
             harvester/orchestrator.py
        (async fetch, retry for 429/5xx, merge, yield)
                              |
                              v
             harvester/output/unified_stream.py
               stdout / file / optional localhost WS
```

## Compliance boundaries

- No anti-bot evasion, CAPTCHA bypass, TLS/browser fingerprint spoofing,
  residential proxy rotation, mobile API signature reverse engineering, or
  hidden WebSocket interception is implemented or documented.
- Sportsbook direct files such as DraftKings, FanDuel, and BetMGM are stubs
  because no approved documented automated API is configured here.
- Betfair is a stub until licensed API credentials are supplied by the user.
- Kalshi is a stub until the documented API terms and required credentials are
  explicitly confirmed for the deployment.
- Polymarket uses only the public CLOB HTTP API and is disabled by default
  (`HARVESTER_ENABLE_POLYMARKET=false`).
- `local-llm/` is used only for fuzzy normalization of raw team/event/market
  strings. It is not used to write scrapers or bypass access controls.

## Implemented The Odds API endpoints

The baseline client uses The Odds API v4:

- `GET /v4/sports`
- `GET /v4/sports/{sport_key}/events`
- `GET /v4/sports/{sport_key}/odds`

Default sports:

- `basketball_nba`
- `americanfootball_nfl`

Default markets:

- `h2h` -> `moneyline`
- `spreads` -> `spread`
- `totals` -> `total`

The API key is read from `THE_ODDS_API_KEY`. `ODDSJAM_API_KEY` and `ODDS_API_KEY`
are also accepted for compatibility with existing repo environment naming.

## Unified output

Each tick emits a JSON array. Required app fields are present, with additional
`sport`, `start_time`, `selection_name`, and `line` fields to make downstream
comparability explicit:

```json
[
  {
    "timestamp": "2026-05-30T18:37:00Z",
    "normalized_event_id": "basketball_nba:2026-06-01T00:00:00+00:00:los-angeles-lakers-boston-celtics",
    "normalized_event_name": "Los Angeles Lakers @ Boston Celtics",
    "market_type": "moneyline",
    "sport": "basketball_nba",
    "start_time": "2026-06-01T00:00:00Z",
    "selection_name": "Boston Celtics",
    "line": null,
    "sources": {
      "the_odds_api:draftkings": {
        "raw_event_name": "Los Angeles Lakers @ Boston Celtics",
        "odds": 120,
        "volume": null,
        "liquidity": null,
        "url": "https://the-odds-api.com/sports-odds-data/basketball_nba/",
        "fetched_at": "2026-05-30T18:37:00Z"
      }
    }
  }
]
```

`arbitrage` is omitted unless at least two comparable binary back/lay-style
prices are available. The Odds API bookmaker American odds do not include a lay
side, so those rows usually omit the block.

## Windows setup for `child@DESKTOP`

Open **Git Bash**:

```bash
cd /c/Users/child/Projects/arbitrage-by-JAC/harvester
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
```

Start Ollama separately and ensure the model named in `OLLAMA_MODEL` is pulled.
Example:

```bash
ollama serve
ollama pull llama3.1
```

Create or update environment files:

```bash
cp ../.env.example ../.env
cp ../local-llm/.env.example ../local-llm/.env
```

Set required values in Git Bash:

```bash
export THE_ODDS_API_KEY="your-paid-the-odds-api-key"
export OLLAMA_BASE_URL="http://localhost:11434"
export OLLAMA_MODEL="llama3.1"
```

Windows `cmd.exe` equivalent:

```cmd
cd harvester
pip install -r requirements.txt
set THE_ODDS_API_KEY=your-paid-the-odds-api-key
python examples/run_harvester.py
```

## Run one tick

From the repo root:

```bash
cd harvester
pip install -r requirements.txt
set THE_ODDS_API_KEY=...
python examples/run_harvester.py
```

In Git Bash, prefer `export THE_ODDS_API_KEY=...` instead of `set`.

## Environment variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `THE_ODDS_API_KEY` | empty | Paid The Odds API key |
| `ODDSJAM_API_KEY` | empty | Compatibility alias for the same key |
| `HARVESTER_SPORTS` | `basketball_nba,americanfootball_nfl` | The Odds API sport keys |
| `HARVESTER_MARKETS` | `h2h,spreads,totals` | Main markets |
| `HARVESTER_REGIONS` | `us` | The Odds API regions |
| `HARVESTER_POLL_INTERVAL_SECONDS` | `30` | Scheduler interval |
| `HARVESTER_ADAPTER_TIMEOUT_SECONDS` | `15` | Per-adapter timeout |
| `HARVESTER_RETRY_ATTEMPTS` | `3` | Retry attempts for HTTP 429/5xx only |
| `HARVESTER_NORMALIZE_CACHE_PATH` | `.cache/harvester/normalize_cache.sqlite3` | sqlite normalization cache |
| `HARVESTER_REFERENCE_PATH` | empty | Optional JSON/YAML alias file |
| `HARVESTER_OUTPUT_PATH` | empty | Write JSON tick to file instead of stdout |
| `HARVESTER_ENABLE_POLYMARKET` | `false` | Enable official public CLOB adapter |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Local Ollama URL |
| `OLLAMA_MODEL` | `llama3.1` | Local model for normalization |
| `LOCAL_LLM_BATCH_SIZE` | `32` | Normalization batch size, clamped to 20-50 |

## Tests

No network is used in tests:

```bash
python -m pytest harvester/tests
```
