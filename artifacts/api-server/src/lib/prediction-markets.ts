import { logger } from "./logger";
import type { OJBookmaker, OJGame, OJMarket, OJOutcome } from "./oddsjam";

const GAMMA_BASE = "https://gamma-api.polymarket.com";

interface PolymarketMarket {
  id?: string;
  question?: string;
  outcomePrices?: string;
  lastTradePrice?: number;
  liquidity?: number;
  volume?: number;
}

function probToAmerican(p: number): number {
  if (p <= 0 || p >= 1) return 100;
  if (p >= 0.5) return Math.round(-(p / (1 - p)) * 100);
  return Math.round(((1 - p) / p) * 100);
}

function parseYesPrice(m: PolymarketMarket): number | null {
  if (m.lastTradePrice != null && m.lastTradePrice > 0 && m.lastTradePrice < 1) {
    return m.lastTradePrice;
  }
  if (m.outcomePrices) {
    try {
      const arr = JSON.parse(m.outcomePrices) as string[];
      const v = parseFloat(arr[0] ?? "");
      if (!Number.isNaN(v)) return v;
    } catch {
      /* ignore */
    }
  }
  return null;
}

/**
 * Public Gamma API — sports-related binary markets as bookmaker legs.
 * https://docs.polymarket.com/api-reference/markets/list-markets
 */
export async function fetchPolymarketBookmakersByEvent(): Promise<
  Map<string, OJBookmaker>
> {
  const map = new Map<string, OJBookmaker>();
  try {
    const url = `${GAMMA_BASE}/markets?active=true&closed=false&limit=100`;
    const res = await fetch(url, { headers: { Accept: "application/json" } });
    if (!res.ok) {
      logger.warn({ status: res.status }, "Polymarket markets fetch failed");
      return map;
    }
    const body = (await res.json()) as PolymarketMarket[] | { data?: PolymarketMarket[] };
    const markets = Array.isArray(body) ? body : (body.data ?? []);
    for (const m of markets) {
      const question = m.question?.trim() ?? "";
      const lower = question.toLowerCase();
      if (!question || (!lower.includes(" vs ") && !lower.includes(" beat "))) {
        continue;
      }
      const yesP = parseYesPrice(m);
      if (yesP == null) continue;
      const key = lower.replace(/\s+/g, " ").trim();
      const price = probToAmerican(yesP);
      const outcome: OJOutcome = { name: question, price };
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
          key: "polymarket",
          title: "Polymarket",
          markets: [market],
        });
      }
    }
  } catch (e) {
    logger.warn({ err: e }, "Polymarket fetch error");
  }
  return map;
}

/** Attach Polymarket bookmaker when event title fuzzy-matches game teams. */
export function mergePolymarketIntoGames(
  games: OJGame[],
  polyByTitle: Map<string, OJBookmaker>,
): OJGame[] {
  if (polyByTitle.size === 0) return games;
  return games.map((g) => {
    const home = g.home_team.toLowerCase();
    const away = g.away_team.toLowerCase();
    for (const [title, book] of polyByTitle) {
      if (
        title.includes(home) &&
        title.includes(away) &&
        !g.bookmakers.some((b) => b.key === "polymarket")
      ) {
        return { ...g, bookmakers: [...g.bookmakers, book] };
      }
    }
    return g;
  });
}
