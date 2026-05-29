"""
Optic Odds (OddsJam) — licensed aggregator for US regulated sportsbooks.

Covers: DraftKings, FanDuel, BetMGM, Caesars, Fanatics, bet365, theScore.
Docs: https://developer.opticodds.com/
"""

from __future__ import annotations

from harvest.config import NC_SPORTSBOOKS, SCAN_TARGETS, HarvestConfig
from harvest.extractors.base import BaseExtractor, FetchLayer
from harvest.models import MarketFragment, MarketType, PlatformKind, PriceQuote
from harvest.resilience import request_json
import httpx

OPTIC_BASE = "https://api.opticodds.com/api/v3"

MAIN_MARKETS = [
    "moneyline",
    "point_spread",
    "total_points",
    "total_goals",
    "player_points",
    "player_assists",
    "player_rebounds",
    "player_pass_yards",
    "player_rush_yards",
    "player_receiving_yards",
]

MARKET_TYPE_MAP: dict[str, MarketType] = {
    "moneyline": MarketType.MONEYLINE,
    "point_spread": MarketType.SPREAD,
    "total_points": MarketType.TOTAL,
    "total_goals": MarketType.TOTAL,
}


class OpticOddsExtractor(BaseExtractor):
    source_id = "optic_odds"
    layer = FetchLayer.A_HTTP_API

    def __init__(self, cfg: HarvestConfig) -> None:
        self._cfg = cfg
        self._key = cfg.optic_odds_api_key

    @property
    def is_configured(self) -> bool:
        return bool(self._key)

    def _fetch(self, path: str, params: dict | list | None = None) -> dict:
        assert self._key
        with httpx.Client(timeout=self._cfg.request_timeout_s) as client:
            url = f"{OPTIC_BASE}{path}"
            headers = {"X-Api-Key": self._key}
            query = self._encode_params(params) if params else None
            return request_json(client, "GET", url, headers=headers, params=query)

    @staticmethod
    def _encode_params(params: dict | list) -> list[tuple[str, str]]:
        """Optic Odds expects repeated query keys for array fields."""
        if isinstance(params, list):
            return params
        out: list[tuple[str, str]] = []
        for key, val in params.items():
            if isinstance(val, list):
                for item in val:
                    out.append((key, str(item)))
            else:
                out.append((key, str(val)))
        return out

    def fetch(self) -> list[MarketFragment]:
        if not self.is_configured:
            return []

        fragments: list[MarketFragment] = []
        for sport, leagues in SCAN_TARGETS:
            for league in leagues:
                fragments.extend(self._fetch_league(sport, league))
        return fragments

    def _fetch_league(self, sport: str, league: str) -> list[MarketFragment]:
        fixture_res = self._fetch(
            "/fixtures/active",
            [("sport", sport), ("league", league), ("is_live", "false")],
        )
        fixtures = [f for f in fixture_res.get("data", []) if f.get("has_odds")][:15]
        if not fixtures:
            return []

        odds_by_fixture: dict[str, list] = {f["id"]: [] for f in fixtures}
        fixture_ids = [f["id"] for f in fixtures]

        for fi in range(0, len(fixture_ids), 5):
            batch_ids = fixture_ids[fi : fi + 5]
            for bi in range(0, len(NC_SPORTSBOOKS), 5):
                book_batch = NC_SPORTSBOOKS[bi : bi + 5]
                batch_params: list[tuple[str, str]] = [("odds_format", "american")]
                for fid in batch_ids:
                    batch_params.append(("fixture_id", fid))
                for bk in book_batch:
                    batch_params.append(("sportsbook", bk))
                for mk in MAIN_MARKETS:
                    batch_params.append(("market", mk))
                batch = self._fetch("/fixtures/odds", batch_params)
                for row in batch.get("data", []):
                    fid = row["id"]
                    if fid in odds_by_fixture:
                        odds_by_fixture[fid].extend(row.get("odds", []))

        out: list[MarketFragment] = []
        fixture_map = {f["id"]: f for f in fixtures}
        for fid, odds_list in odds_by_fixture.items():
            if not odds_list:
                continue
            fx = fixture_map[fid]
            home = (
                fx.get("home_team_display")
                or (fx.get("home_competitors") or [{}])[0].get("name")
                or "Home"
            )
            away = (
                fx.get("away_team_display")
                or (fx.get("away_competitors") or [{}])[0].get("name")
                or "Away"
            )
            by_book: dict[str, list] = {}
            for o in odds_list:
                by_book.setdefault(o["sportsbook"], []).append(o)

            for book_name, entries in by_book.items():
                by_line: dict[str, list] = {}
                for e in entries:
                    lk = f"{e['market_id']}::{e.get('grouping_key', '')}"
                    by_line.setdefault(lk, []).append(e)
                for line_key, group in by_line.items():
                    market_id = group[0]["market_id"]
                    mtype = MARKET_TYPE_MAP.get(
                        market_id.split("_")[0] if "_" in market_id else market_id,
                        MarketType.MONEYLINE,
                    )
                    if "player_" in market_id:
                        mtype = MarketType.PLAYER_PROP
                    quotes = [
                        PriceQuote(
                            platform=book_name.lower().replace(" ", "_"),
                            outcome_label=e["name"],
                            american_odds=int(e["price"]),
                            line=e.get("points"),
                            raw=e,
                        )
                        for e in group
                    ]
                    out.append(
                        MarketFragment(
                            source=book_name.lower().replace(" ", "_"),
                            platform_kind=PlatformKind.SPORTSBOOK,
                            sport=sport,
                            league=league,
                            home_team=home,
                            away_team=away,
                            commence_time=fx.get("start_date"),
                            market_type=mtype,
                            market_key=line_key,
                            quotes=quotes,
                            metadata={"fixture_id": fid, "layer": self.layer.value},
                        )
                    )
        return out
