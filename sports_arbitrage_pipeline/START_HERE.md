# START HERE — you already have the repo

If you are in `~/Projects/arbitrage-by-JAC`, **do not clone again**.

```bash
cd ~/Projects/arbitrage-by-JAC
git pull origin cursor/local-llm-normalization-4fea
cd sports_arbitrage_pipeline
bash bootstrap.sh
source ./activate_venv.sh
python arbitrage_orchestrator.py
```

## Windows activate (never use `venv/bin/activate`)

```bash
source ./activate_venv.sh
```

## API key

```bash
nano ../harvester/.env
```

Set `ODDS_API_KEY=your_key`

## If `git pull` says branch not found

```bash
git fetch origin
git pull origin cursor/local-llm-normalization-4fea
```

## Run from repo root (alternative)

```bash
cd ~/Projects/arbitrage-by-JAC
source sports_arbitrage_pipeline/activate_venv.sh
python arbitrage_orchestrator.py
```
