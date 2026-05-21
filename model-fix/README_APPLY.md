# model.py fix — "Feature shape mismatch" error

## What went wrong

The trained model files in the repo were saved before `feature_cols` was
being stored inside them. When the updated code loaded them, it fell back
to the *current* feature list (43 features), but the model was trained
on only 34. XGBoost caught the mismatch:

    ValueError: Feature shape mismatch, expected: 34, got 43

## What the fix does

`models/model.py` now detects the training width directly from the model
itself (`n_features_in_` / XGBoost booster), then slices
`FEATURE_COLS[:N]` to get exactly the features it was trained on. This
works safely because new features (injury, arbitrage) were always
appended to the *end* of `FEATURE_COLS`.

New model files saved after retraining will include `feature_cols` in
their bundle and skip the detection step entirely.

---

## Apply

### Option A — GitHub website (easiest)

1. Go to your repo → `models/model.py` → click the pencil (Edit) icon
2. Replace the entire file contents with the `model.py` in this bundle
3. Commit directly to `main`

### Option B — patch

```bash
cd /path/to/Line-Tracker-Model
git apply model_fix.patch
git add models/model.py
git commit -m "Fix: detect legacy model feature width to resolve shape mismatch"
git push
```

### Option C — copy the file

```bash
cp model.py /path/to/Line-Tracker-Model/models/model.py
cd /path/to/Line-Tracker-Model
git add models/model.py
git commit -m "Fix: detect legacy model feature width"
git push
```

---

## After applying

Re-run the workflow from the Actions tab. The pipeline will load the
old 34-feature models correctly and score today's slate.

Eventually, once you run `python train.py` with new historical data, the
models will be retrained on all 43 features (including injuries and
arbitrage) and saved with the full feature list. After that, the
detection step is no longer needed.
