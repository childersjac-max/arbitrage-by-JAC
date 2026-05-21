# OddsJam adapter — drop-in data-source layer

This bundle adds a swappable data-source abstraction to your model. The Odds API stays the default; OddsJam becomes a one-env-var switch when you're ready.

---

## What ships in this bundle

**4 new files** (all live under a new `data/sources/` package):

| File | Purpose |
|---|---|
| `data/sources/__init__.py` | Factory: `get_source()` reads `ODDS_DATA_SOURCE` and returns the right adapter |
| `data/sources/base.py` | `OddsSource` ABC — defines the canonical interface every provider must implement |
| `data/sources/the_odds_api.py` | Existing The Odds API logic, refactored behind the interface |
| `data/sources/oddsjam.py` | New OddsJam adapter, ready to use once you set the env vars |

**4 modified files** — every place in the codebase that previously called `requests.get("https://api.the-odds-api.com/...")` now goes through the source factory:

| File | What changed |
|---|---|
| `scraper.py` | `fetch_odds()` and `fetch_player_props_for_event()` delegate to the source. Startup guard now checks the right env var for the selected source. |
| `data/historical.py` | `fetch_historical_odds()` and `fetch_historical_scores()` delegate. Source-aware key check. |
| `data/results.py` | `fetch_scores()` delegates. Removed direct `requests` use. |
| `bootstrap_history.py` | `fetch_historical_odds()` delegates. Source-aware key check. |

Nothing else in the codebase changes. Models, features, scoring, Kelly sizing, scoring schema — all untouched.

---

## How to apply

### Option 1 — patch
```bash
cd Line-Tracker-Model
git apply oddsjam_adapter.patch
```

### Option 2 — copy files
Copy everything under `changed_files/` over the matching paths in your repo, preserving directory structure:

```
changed_files/scraper.py                  -> scraper.py
changed_files/bootstrap_history.py        -> bootstrap_history.py
changed_files/data/historical.py          -> data/historical.py
changed_files/data/results.py             -> data/results.py
changed_files/data/sources/__init__.py    -> data/sources/__init__.py   (new)
changed_files/data/sources/base.py        -> data/sources/base.py       (new)
changed_files/data/sources/the_odds_api.py -> data/sources/the_odds_api.py (new)
changed_files/data/sources/oddsjam.py     -> data/sources/oddsjam.py    (new)
```

### Verify
```bash
python -m py_compile data/sources/__init__.py data/sources/base.py \
  data/sources/the_odds_api.py data/sources/oddsjam.py \
  scraper.py data/historical.py data/results.py bootstrap_history.py
```

Then a no-network smoke test (already passes for me):
```bash
python -c "from data.sources import get_source; print(get_source().name)"
# -> the_odds_api
ODDS_DATA_SOURCE=oddsjam ODDSJAM_API_KEY=dummy python -c "from data.sources import get_source; print(get_source().name)"
# -> oddsjam
```

---

## How to switch sources

Stay on The Odds API (default — no change needed):
```bash
unset ODDS_DATA_SOURCE                # or omit
export ODDS_API_KEY=...               # as before
```

Switch to OddsJam:
```bash
export ODDS_DATA_SOURCE=oddsjam
export ODDSJAM_API_KEY=<your key>
```

Run anything as normal:
```bash
python pipeline.py --mode scrape
python pipeline.py --mode historical --days 30
python pipeline.py --mode results
python pipeline.py --mode predict --bankroll 10000
```

---

## ⚠ ONE-TIME OddsJam configuration step (5 minutes after signup)

The OddsJam developer portal is gated behind a paid subscription, so I couldn't pull their OpenAPI schema directly. The adapter at `data/sources/oddsjam.py` is built against OddsJam's publicly documented v2 API surface and the conventional endpoint/field names. **Once you have your dashboard access, open `https://docs.oddsjam.com/` and confirm these constants near the top of that file:**

```python
BASE_URL = "https://api-external.oddsjam.com/api/v2"   # confirm host + version
USE_HEADER_AUTH = False                                 # True if your account uses X-API-Key header instead of ?key=
HEADER_AUTH_NAME = "X-API-Key"

PATHS = {
    "games":           "/games",
    "game_odds":       "/game-odds",
    "historical_odds": "/historical-odds",
    "scores":          "/scores",
    "injuries":        "/injuries",
}

SPORT_TO_LEAGUE = {"americanfootball_nfl": "NFL", "basketball_nba": "NBA", ...}
SPORT_TO_SPORT  = {"americanfootball_nfl": "football", ...}
MARKET_NAME     = {"h2h": "Moneyline", "spreads": "Point Spread", "totals": "Total Points"}
BOOK_REMAP      = {"DraftKings": "draftkings", "Pinnacle": "pinnacle", ...}
```

If anything is misnamed, `fetch_current_odds()` will return `[]` and print the HTTP body — that's your debugging hook. The normalize layer (`_normalize_events`, `_normalize_scores`) is also commented and edit-friendly if OddsJam ever uses field names different from what we assumed (e.g. `home_team_score` vs `home_score`).

The rest of the codebase stays identical — every consumer just sees the canonical Odds API JSON shape.

---

## What you gain by switching to OddsJam

| Capability | Now you get… |
|---|---|
| Sportsbooks | 100+ (vs ~40), including full sharp coverage (Pinnacle, Circa, BookMaker) |
| Player props | Real-time depth across all major sports (vs limited on The Odds API) |
| Historical odds | Full tick-by-tick line history, multi-year |
| Scores | Same endpoint, better real-time freshness |
| Injuries | Bonus — `OddsJamSource.fetch_injuries(sport_key)` is wired up; not yet used by `data/injuries.py` (if you want, we can wire that next) |
| Push feeds | Available but not used by this adapter (we're polling). Worth wiring up later if you go live-betting. |

What does NOT change just by switching:
- VSiN public/sharp split scraping is still in `scraper.py`. OddsJam doesn't expose money/ticket splits, so VSiN stays where it is.
- Rate-limit awareness, retries, and chunking. The OddsJam adapter currently chunks game IDs at 50/request — adjust if your plan caps differ.

---

## Smoke tests it already passes (verified locally before shipping)

- All 8 changed files pass `python -m py_compile`
- `get_source()` with no env returns `the_odds_api`
- `get_source('oddsjam')` returns `oddsjam`
- `get_source('nope')` raises `ValueError` with a helpful message
- `scraper`, `data.historical`, `data.results`, `bootstrap_history` all import cleanly with `ODDS_DATA_SOURCE=oddsjam` selected (no API calls fired)

---

## Recommended first run after you have OddsJam access

```bash
# 1) confirm the constants in data/sources/oddsjam.py against your docs portal
# 2) quick sanity check (1 sport, no models touched)
ODDS_DATA_SOURCE=oddsjam ODDSJAM_API_KEY=... python -c "
from data.sources import get_source
s = get_source()
events = s.fetch_current_odds('basketball_nba')
print(f'Got {len(events)} NBA events')
if events:
    e = events[0]
    print(' bookmakers:', [b['key'] for b in e['bookmakers']][:5])
    print(' markets   :', [m['key'] for bm in e['bookmakers'] for m in bm['markets']][:5])
"
# 3) Then bulk historical pull -- this is where OddsJam earns its money:
ODDS_DATA_SOURCE=oddsjam ODDSJAM_API_KEY=... python pipeline.py --mode historical --days 90
# 4) Retrain
python train.py --sport all --market all
# 5) Live slate
ODDS_DATA_SOURCE=oddsjam ODDSJAM_API_KEY=... python pipeline.py --mode predict --bankroll 10000
```
