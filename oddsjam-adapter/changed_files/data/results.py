# data/results.py

import json
import os
from pathlib import Path
from configs.config import SPORTS, OUTCOMES_FILE
from data.sources import get_source

ODDS_DATA_SOURCE = os.environ.get("ODDS_DATA_SOURCE", "the_odds_api").strip().lower()

# Lazy source instance
_SOURCE = None
def _src():
    global _SOURCE
    if _SOURCE is None:
        _SOURCE = get_source(ODDS_DATA_SOURCE)
    return _SOURCE


def fetch_scores(sport_key, days_from=3):
    return _src().fetch_scores(sport_key, days_from=days_from)


def load_outcomes():
    p = Path(OUTCOMES_FILE)
    if p.exists():
        with open(p) as f:
            return json.load(f)
    return {}


def save_outcomes(outcomes):
    with open(OUTCOMES_FILE, "w") as f:
        json.dump(outcomes, f, indent=2)


def fetch_and_store_outcomes(days_from=3):
    outcomes = load_outcomes()
    new_count = 0
    for sport_key in SPORTS:
        print(f"  Fetching scores: {sport_key}")
        try:
            games = fetch_scores(sport_key, days_from=days_from)
        except Exception as e:
            print(f"  Error: {e}")
            continue
        for game in games:
            if not game.get("completed"):
                continue
            eid = game.get("id")
            if f"{eid}_home_ml" in outcomes:
                continue
            home = game.get("home_team", "")
            away = game.get("away_team", "")
            scores = {s["name"]: int(float(s["score"])) for s in (game.get("scores") or []) if s.get("score")}
            hs = scores.get(home)
            as_ = scores.get(away)
            if hs is None or as_ is None:
                continue
            outcomes[f"{eid}_home_ml"]    = int(hs > as_)
            outcomes[f"{eid}_away_ml"]    = int(as_ > hs)
            outcomes[f"{eid}_total"]      = hs + as_
            outcomes[f"{eid}_home_score"] = hs
            outcomes[f"{eid}_away_score"] = as_
            new_count += 1
    save_outcomes(outcomes)
    print(f"  Added {new_count} new results. Total: {len([k for k in outcomes if k.endswith('_home_ml')])}")
    return outcomes
