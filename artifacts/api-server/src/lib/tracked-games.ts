import { getOdds } from "./oddsjam";
import { SCAN_TARGETS } from "./scan-config";

export interface TrackedOddsRow {
  bookmaker: string;
  bookmakerTitle: string;
  market: string;
  outcome: string;
  price: number;
  point?: number;
}

export interface TrackedGame {
  id: string;
  sport: string;
  homeTeam: string;
  awayTeam: string;
  commenceTime: string;
  bookmakerOdds: TrackedOddsRow[];
}

export async function getTrackedGames(params: {
  sport: string;
  markets?: string;
  days?: number;
}): Promise<TrackedGame[]> {
  const league = SCAN_TARGETS.find((t) => t.sport === params.sport)?.leagues[0];
  const games = await getOdds({
    sport: params.sport,
    league,
    markets: params.markets,
  });

  const cutoff = Date.now() + (params.days ?? 3) * 86400000;

  return games
    .filter((g) => new Date(g.commence_time).getTime() <= cutoff)
    .map((g) => {
      const bookmakerOdds: TrackedOddsRow[] = [];
      for (const b of g.bookmakers) {
        for (const m of b.markets) {
          for (const o of m.outcomes) {
            bookmakerOdds.push({
              bookmaker: b.key,
              bookmakerTitle: b.title,
              market: m.key,
              outcome: o.name,
              price: o.price,
              point: o.point,
            });
          }
        }
      }
      return {
        id: g.id,
        sport: g.sport_key,
        homeTeam: g.home_team,
        awayTeam: g.away_team,
        commenceTime: g.commence_time,
        bookmakerOdds,
      };
    });
}
