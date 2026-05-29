"""
The Odds API baseline integrator (paid subscription).

Covers retail US books returned by the API: DraftKings, FanDuel, BetMGM,
Caesars (williamhill_us), Fanatics, bet365, and related keys per your plan.
"""

from __future__ import annotations

from typing import Any, Iterable

from arb_harvest.config import HarvestConfig, US_SPORTSBOOK_KEYS
from arb_harvest.models import MarketQuote, NormalizedEvent, OutcomeQuote, SourceBook
from arb_harvest.net import PoliteHttpClient
from arb_harvest.normalize.matcher import build_normalized_event_name


class TheOddsApiBaseline:
    BASE = "https://api.the-odds-api.com/v4"

    def __init__(self, config: HarvestConfig, http: PoliteHttpClient | None = None):
        self.config = config
        self.http = http or PoliteHttpClient(requests_per_second=config.http_rps)
        self._api_key = config.odds_api_key

    def _params(self, extra: dict[str, Any]) -> dict[str, Any]:
        return {**extra, "apiKey": self._api_key}

    def fetch_sport_odds(self, sport_key: str) -> list[dict[str, Any]]:
        if not self._api_key:
            return []
        url = f"{self.BASE}/sports/{sport_key}/odds"
        data = self.http.get_json(
            url,
            params=self._params(
                {
                    "regions": self.config.regions,
                    "markets": ",".join(self.config.baseline_markets),
                    "oddsFormat": "american",
                }
            ),
        )
        return data if isinstance(data, list) else []

    def fetch_event_odds(
        self,
        sport_key: str,
        event_id: str,
        markets: Iterable[str],
    ) -> dict[str, Any]:
        if not self._api_key:
            return {}
        url = f"{self.BASE}/sports/{sport_key}/events/{event_id}/odds"
        data = self.http.get_json(
            url,
            params=self._params(
                {
                    "regions": self.config.regions,
                    "markets": ",".join(markets),
                    "oddsFormat": "american",
                }
            ),
        )
        return data if isinstance(data, dict) else {}

    def list_events(self, sport_key: str) -> list[dict[str, Any]]:
        if not self._api_key:
            return []
        url = f"{self.BASE}/sports/{sport_key}/events"
        data = self.http.get_json(url, params=self._params({}))
        return data if isinstance(data, list) else []

    def events_to_normalized(self, raw_events: list[dict[str, Any]], sport_key: str) -> list[NormalizedEvent]:
        out: list[NormalizedEvent] = []
        for ev in raw_events:
            home = ev.get("home_team") or ""
            away = ev.get("away_team") or ""
            norm = build_normalized_event_name(home, away)
            books: list[SourceBook] = []
            for bm in ev.get("bookmakers") or []:
                key = (bm.get("key") or "").lower()
                if key and key not in US_SPORTSBOOK_KEYS and key not in (
                    "pinnacle",
                    "betfair_ex_uk",
                    "betfair_ex_eu",
                    "smarkets",
                ):
                    # Still ingest sharp/exchange keys when API returns them
                    pass
                markets: list[MarketQuote] = []
                for mkt in bm.get("markets") or []:
                    outcomes: list[OutcomeQuote] = []
                    for o in mkt.get("outcomes") or []:
                        price = o.get("price")
                        if price is None:
                            continue
                        outcomes.append(
                            OutcomeQuote(
                                name=str(o.get("name", "")),
                                price_american=price,
                                point=o.get("point"),
                            )
                        )
                    if outcomes:
                        markets.append(
                            MarketQuote(
                                key=mkt.get("key", "unknown"),
                                outcomes=outcomes,
                                last_update=mkt.get("last_update"),
                            )
                        )
                if markets:
                    books.append(
                        SourceBook(
                            source_id=key or "unknown",
                            title=bm.get("title") or key,
                            markets=markets,
                            raw=bm,
                        )
                    )
            out.append(
                NormalizedEvent(
                    event_id=ev.get("id", norm),
                    sport_key=sport_key,
                    normalized_name=norm,
                    home_team=home,
                    away_team=away,
                    commence_time=ev.get("commence_time", ""),
                    books=books,
                )
            )
        return out

    def pull_all_sports(self) -> list[NormalizedEvent]:
        events: list[NormalizedEvent] = []
        for sport in self.config.sport_keys:
            raw = self.fetch_sport_odds(sport)
            events.extend(self.events_to_normalized(raw, sport))
        return events

    def enrich_with_event_props(self, events: list[NormalizedEvent]) -> list[NormalizedEvent]:
        """Use paid per-event endpoint for alternate/player markets (no scraping)."""
        if not self.config.enable_event_props:
            return events
        enriched: list[NormalizedEvent] = []
        for ev in events:
            prop_markets = self.config.prop_markets_by_sport.get(ev.sport_key)
            if not prop_markets:
                enriched.append(ev)
                continue
            payload = self.fetch_event_odds(ev.sport_key, ev.event_id, prop_markets)
            if not payload:
                enriched.append(ev)
                continue
            extra = self.events_to_normalized([payload], ev.sport_key)
            if not extra:
                enriched.append(ev)
                continue
            merged_books = {b.source_id: b for b in ev.books}
            for book in extra[0].books:
                existing = merged_books.get(book.source_id)
                if existing:
                    existing.markets.extend(book.markets)
                else:
                    merged_books[book.source_id] = book
            enriched.append(
                NormalizedEvent(
                    event_id=ev.event_id,
                    sport_key=ev.sport_key,
                    normalized_name=ev.normalized_name,
                    home_team=ev.home_team,
                    away_team=ev.away_team,
                    commence_time=ev.commence_time,
                    books=list(merged_books.values()),
                )
            )
        return enriched
