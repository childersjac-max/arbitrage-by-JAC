# GitHub Actions workflow — Daily Bet Slate at 3 PM ET

## How to add this to your repo

Copy the `.github/` folder from this bundle into the root of your
`Line-Tracker-Model` repo and push:

```bash
cp -r .github /path/to/Line-Tracker-Model/
cd /path/to/Line-Tracker-Model
git add .github/workflows/daily_pipeline.yml
git commit -m "Add daily pipeline workflow (3 PM ET)"
git push
```

That's it. GitHub will automatically pick it up.

---

## What it does every day at 3 PM ET

1. Pulls the latest odds from all books via OddsJam
2. Saves line movement snapshots to `line_history/`
3. Fetches yesterday's results and updates `outcomes.json`
4. Scores today's slate with your trained models
5. Uploads `bet_slate_latest.csv` as a downloadable artifact
6. Prints a summary of today's bets in the Actions log

---

## Where to see the output

Go to your repo on GitHub → **Actions** tab → click the latest
**Daily Bet Slate** run → scroll to the bottom → click
**bet-slate-XXXXXX** under Artifacts to download the CSV.

The summary is also printed in the run log so you can read it without
downloading anything.

---

## Run it on demand (any time)

Go to **Actions → Daily Bet Slate → Run workflow** (top right).
You can override the bankroll and minimum-signals filter before running.

---

## Time zone note

GitHub Actions cron runs in UTC. The workflow is set to `0 19 * * *`
(19:00 UTC = 3:00 PM EDT, March–November).

In winter when the clocks fall back (EST = UTC-5), 3 PM ET becomes
20:00 UTC. To keep it at exactly 3 PM in winter too, change the cron
line to `"0 20 * * *"` in November and back to `"0 19 * * *"` in March.

---

## Secret required

Make sure `ODDSJAM_API_KEY` is set in:
**Repo Settings → Secrets and variables → Actions**

The workflow will fail with a 401 error if the secret is missing.
