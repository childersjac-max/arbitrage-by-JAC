# OddsJam max-history + arbitrage angle — apply guide

This bundle does two things on top of the OddsJam adapter you already
have installed:

1. **Pulls as much history as OddsJam will give you** — all 6 leagues,
   8 snapshots/day, up to 365 days back, with resume support so a
   re-run only fetches what's missing.
2. **Adds an `ARBITRAGE` angle to the model** — every snapshot is now
   scanned for cross-book 2-way arbs (h2h / matched-line spreads /
   matched-line totals). When this side is one leg of a positive arb,
   the bet shows up in the slate tagged `ARBITRAGE(x.xx%)` with the
   partner book/price/line surfaced as new columns. Three numeric arb
   features (`is_arb_side`, `arb_margin_pct`, `arb_book_count`) are
   added to the model's input vector so it can learn that a market
   disagreeing with itself is a real signal.

The arb detection is **provider-agnostic**: it runs on the odds we
already pull, so it works on The Odds API too. OddsJam's pre-computed
`/arbitrage` feed is wired up as an optional bonus via
`OddsJamSource.fetch_arbitrage_opportunities()`.

---

## Files in this bundle

```
oddsjam-history-arb/
├── README_APPLY.md                    ← this file
├── oddsjam_history_arb.patch          ← apply with `git apply`
├── oddsjam_history_arb.patch.txt      ← same patch, .txt extension for browsers
└── changed_files/                     ← drop-in copies if you'd rather not patch
    ├── bootstrap_oddsjam.py           (NEW — repo root)
    ├── features/
    │   ├── arbitrage.py               (NEW)
    │   └── movement.py                (modified)
    ├── data/
    │   ├── historical.py              (modified)
    │   └── sources/
    │       ├── base.py                (modified — adds arb hook + max-days props)
    │       └── oddsjam.py             (modified — adds arb endpoint + max-days)
    ├── models/scorer.py               (modified — surfaces arb in slate)
    ├── pipeline.py                    (modified — adds arb columns to CSV)
    └── configs/config.py              (modified — adds MIN_ARB_MARGIN_PCT)
```

---

## Apply

### Option A — patch
```bash
cd /path/to/Line-Tracker-Model
git apply --whitespace=nowarn oddsjam_history_arb.patch
```

### Option B — drop-in copy
```bash
cd /path/to/Line-Tracker-Model
cp -r changed_files/* .
```

---

## Run the max-history pull

```bash
export ODDS_DATA_SOURCE=oddsjam
export ODDSJAM_API_KEY=<your key>

# Estimate first (no API calls):
python bootstrap_oddsjam.py --dry-run

# Full 365-day pull, all 6 leagues, 8 snapshots/day:
python bootstrap_oddsjam.py

# Or scope it down:
python bootstrap_oddsjam.py --days 90
python bootstrap_oddsjam.py --sports NBA,NHL,NFL --hours 9,15,21
```

Resume is on by default — kill the process at any point and re-run, it
will skip the (sport, timestamp) pairs already saved in `line_history/`.

After the pull:
```bash
python train.py
python pipeline.py --mode predict
```

You can still use the existing daily flow (`python pipeline.py --mode
historical --days N`) — it now picks up the source's max-days settings
automatically and supports resume too.

---

## Verify the arbitrage angle

A real arb on the slate looks like this:

```
sport  market  side       american_odds  edge_pct  bet_usd  signals
NBA    h2h     Lakers     +120           4.21       82.40   ARBITRAGE(2.31%), SHARP_MONEY
```

And the CSV (`output/bet_slate_latest.csv`) gets seven new columns:
```
is_arb_side, arb_margin_pct, arb_book_count,
arb_book, arb_partner_book, arb_partner_price, arb_partner_line
```

Tune the threshold in `configs/config.py`:
```python
MIN_ARB_MARGIN_PCT = 0.5   # ignore arbs thinner than 0.5% (default)
```
Set it to `0.0` to surface every micro-arb.

---

## Env-var knobs (all optional)

| Variable                   | Default (OddsJam)                | Purpose                                                       |
|----------------------------|----------------------------------|---------------------------------------------------------------|
| `HISTORICAL_SPORTS`        | all 6 leagues                    | Comma-separated `sport_keys` to limit the pull                |
| `DAILY_HOURS`              | `3,7,10,13,16,19,21,23`          | UTC sample hours per day                                      |
| `HISTORICAL_PULL_SLEEP`    | `0.5`                            | Seconds between calls (be polite to OddsJam)                  |
| `ODDS_DATA_SOURCE`         | `the_odds_api`                   | Set to `oddsjam` to use OddsJam everywhere                    |
| `ODDSJAM_API_KEY`          | —                                | Required when `ODDS_DATA_SOURCE=oddsjam`                      |

Defaults stay backwards-compatible: with no env vars set, the pipeline
behaves exactly as it did before for The Odds API users (3 sports,
4x/day, 30-day window).

---

## What gets added to the model

`features/movement.py` now puts these in `FEATURE_COLS`, so any model
you retrain after the bundle picks them up:

- `is_arb_side`     — 1.0 if this side is one leg of a ≥ `MIN_ARB_MARGIN_PCT` arb
- `arb_margin_pct`  — the % profit margin on the best arb pair found
- `arb_book_count`  — how many books on this side participate in some arb

The string fields (`arb_book`, `arb_partner_book`, `arb_partner_price`,
`arb_partner_line`) deliberately stay OUT of the model input vector but
DO show up in the slate CSV so you can place the arb manually.

Old models trained before this bundle still load fine — XGBoost ignores
extra columns at predict time. Retraining with `python train.py` after a
new historical pull is when the model actually starts using the arb
signals.

---

## What I verified before shipping

- All 9 files compile clean (`python -m py_compile`)
- Arb detection on a synthetic snapshot returns 6.93% margin for a known
  +120 / +110 pair (matches hand calc) and correctly returns 0 for a
  -110 / -110 pair and for unmatched-line spreads
- Full import chain works under both `ODDS_DATA_SOURCE=oddsjam` and
  `ODDS_DATA_SOURCE=the_odds_api`
- `bootstrap_oddsjam.py --dry-run` prints accurate call estimates
- `is_arb_side` and `arb_margin_pct` show up in `FEATURE_COLS`

---

## ⚠ Same one-time note as the previous bundle

OddsJam's docs portal is gated behind their paid plan, so the
`PATHS["arbitrage"] = "/arbitrage"` constant and the field names in
`fetch_arbitrage_opportunities()` are written against the conventional
v2 surface. Once you're in the docs, double-check:

- `PATHS["arbitrage"]` (currently `/arbitrage`)
- The legs payload field name (`legs` vs `bets`)
- The margin field name (`profit_margin` / `margin_pct` /
  `arbitrage_percentage` — the adapter accepts all three)

If anything is off, the fallback is silent — local arb detection from
`features/arbitrage.py` keeps working regardless. Fixing the OddsJam
endpoint constant just adds OddsJam's pre-computed feed on top.
