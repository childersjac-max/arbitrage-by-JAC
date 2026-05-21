# Line-Tracker-Model — Tier 1 improvements

Implements fixes #1, #2, #3, #4, #6, #16, #21 from the review.

## How to apply

Two equivalent options.

### Option A — Apply the patch (preferred)

```bash
cd Line-Tracker-Model
git apply /path/to/improvements.patch
git status                # sanity check
git add -A && git commit -m "Tier 1 model improvements"
```

If `git apply` rejects because of local divergence, use `git apply --3way` or fall back to Option B.

### Option B — Drop in the changed files

Copy each file from `changed_files/` into the same path in your repo, replacing the original.

```bash
cd Line-Tracker-Model
cp -r /path/to/changed_files/* .
git status
```

## After applying

1. **Retrain.** The label set, feature set, and CV strategy all changed:
   ```bash
   python train.py --sport all --market all
   ```
   Expect AUC numbers to **drop** vs the old reports — that's intended (the old numbers were inflated by random-shuffle CV on time-series data). Calibration (Brier score) is now also reported.

2. **Re-score the slate.**
   ```bash
   python pipeline.py --mode predict --bankroll 10000
   ```
   The new `bet_slate_latest.csv` contains:
   - `model_prob` — raw model probability
   - `sized_prob` — α·model + (1−α)·fair (this is what Kelly uses)
   - `fair_prob` — **no-vig** Pinnacle prob (the real fair line)
   - `edge_pct` — edge using sized_prob (recommended)
   - `edge_pct_raw` — edge using raw model_prob (diagnostic)
   - `shrinkage_alpha` — the α in use (default 0.5)
   - `clv_signed_train` — historical CLV feature value
   - `trained_on` — `real` or `synthetic` (DO NOT bet rows tagged synthetic)

3. **Tune α.** `PROB_SHRINKAGE_ALPHA` in `configs/config.py` defaults to **0.5**.
   - Closer to 1.0 → more aggressive (original behavior, higher drawdown risk)
   - Closer to 0.0 → almost never bets (zero edge after shrinkage)
   - Backtest at 0.3 / 0.5 / 0.7 once you have real outcomes.

## What changed (file by file)

| File | Change |
|---|---|
| `configs/config.py` | New: `PROB_SHRINKAGE_ALPHA`, `MIN_MODEL_PROB`, `TIMESERIES_CV_SPLITS`, `CALIBRATION_TAIL_FRACTION`. `MIN_SAMPLES_TO_TRAIN` raised 10 → 50. |
| `utils/odds_math.py` | New helper `no_vig_prob_for_side(snap, market, side, book)` — devigs Pinnacle prices for any market. |
| `features/movement.py` | Added `pin_no_vig_prob`, `pin_no_vig_prob_open`, `pin_no_vig_prob_close`, `clv_signed`, `clv_abs`, `has_clv`. Surfaces `commence_time`. Old `pin_implied_prob` retained for backward compatibility. |
| `data/labeler.py` | Pushes (margin+line == 0 for spreads, total == line for totals) now return `outcome=None` instead of being mislabeled as losses. They're excluded from training. |
| `models/model.py` | `StratifiedKFold` → **`TimeSeriesSplit`** (no more future-leakage in CV). **Prefit calibration** on a chronological 20% tail (`cv="prefit"`), not the same data the model was trained on. Adds Brier score. Saves `trained_on`, `trained_at`, `feature_cols` in the JSON sidecar. Adaptive `scale_pos_weight` for class imbalance. |
| `train.py` | Sorts by `commence_time` before training. Passes `trained_on=("real" \| "synthetic")` to the model so the tag is persisted. |
| `models/scorer.py` | Uses `pin_no_vig_prob` (not the with-vig prob) as fair_prob. Applies α-shrinkage before Kelly. Enforces `MIN_MODEL_PROB`. Tags every recommendation with `trained_on` and logs a loud warning when synthetic-trained models are used. |
| `pipeline.py` | CSV headers updated to expose the new diagnostic columns. |

## Things to watch after retraining

- **Models trained on synthetic outcomes** (because `outcomes.json` is still mostly empty) will load with `trained_on=synthetic`. Every row of the slate will be tagged accordingly. **Do not bet those rows for real money** — they're mathematically guaranteed to have ~zero true edge, since synthetic labels are sampled from the no-vig market.
- **Fewer bets clear the threshold** after shrinkage. That's working as intended — those bets had inflated edges from with-vig fair prob.
- **AUC drops** in CV reports. Also intended — `TimeSeriesSplit` is honest where `StratifiedKFold` was leaky.
