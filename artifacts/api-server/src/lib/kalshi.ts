import { logger } from "./logger";
import type { OJBookmaker, OJGame, OJMarket, OJOutcome } from "./oddsjam";

const KALSHI_BASE = "https://api.elections.kalshi.com/trade-api/v2";

interface KalshiMarket {
  ticker: string;
  title: string;
  yes_ask?: number;
  yes_bid?: number;
  no_ask?: number;
  no_bid?: number;
  status: string;
  close_time?: string;
}

/** Convert Kalshi cents probability (0–100) to American odds. */
function probCentsToAmerican(cents: number): number {
  const p = cents / 100;
  if (p <= 0 || p >= 1) return 100;
  if (p >= 0.5) return Math.round(-(p / (1 - p)) * 100);
  return Math.round(((1 - p) / p) * 100);
}

/**
 * Fetch open sports-related Kalshi markets and expose as bookmaker legs
 * keyed by a normalized event title for merging with Optic Odds games.
 */
export async function fetchKalshiBookmakersByEvent(): Promise<
  Map<string, OJBookmaker>
> {
  const map = new Map<string, OJBookmaker>();
  try {
    const url = `${KALSHI_BASE}/markets?status=open&limit=200`;
    const res = await fetch(url, { headers: { Accept: "application/json" } });
    if (!res.ok) {
      logger.warn({ status: res.status }, "Kalshi markets fetch failed");
      return map;
    }
    const body = (await res.json()) as { markets?: KalshiMarket[] };
    for (const m of body.markets ?? []) {
      const title = m.title?.toLowerCase() ?? "";
      if (
        !title ||
        (!title.includes(" vs ") &&
          !title.includes(" beat ") &&
          !title.includes("winner"))
      ) {
        continue;
      }
      const key = title.replace(/\s+/g, " ").trim();
      const yesCents = m.yes_ask ?? m.yes_bid;
      if (yesCents == null) continue;
      const price = probCentsToAmerican(yesCents);
      const outcome: OJOutcome = { name: m.title, price };
      const market: OJMarket = {
        key: "moneyline",
        last_update: new Date().toISOString(),
        outcomes: [outcome],
      };
      const existing = map.get(key);
      if (existing) {
        existing.markets.push(market);
      } else {
        map.set(key, {
          key: "kalshi",
          title: "Kalshi",
          markets: [market],
        });
      }
    }
  } catch (e) {
    logger.warn({ err: e }, "Kalshi fetch error");
  }
  return map;
}

/** Attach Kalshi bookmaker to games when titles loosely match. */
export function mergeKalshiIntoGames(
  games: OJGame[],
  kalshiByTitle: Map<string, OJBookmaker>,
): OJGame[] {
  if (kalshiByTitle.size === 0) return games;
  return games.map((g) => {
    const hay = `${g.home_team} vs ${g.away_team}`.toLowerCase();
    for (const [title, book] of kalshiByTitle) {
      const home = g.home_team.toLowerCase();
      const away = g.away_team.toLowerCase();
      if (
        title.includes(home) &&
        title.includes(away) &&
        !g.bookmakers.some((b) => b.key === "kalshi")
      ) {
        return { ...g, bookmakers: [...g.bookmakers, book] };
      }
      if (hay && title.includes(hay)) {
        return { ...g, bookmakers: [...g.bookmakers, book] };
      }
    }
    return g;
  });
}
