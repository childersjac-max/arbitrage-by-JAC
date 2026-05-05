import type { OJGame } from "./oddsjam-client";

export interface ArbLeg {
  bookmaker: string;
  bookmakerTitle: string;
  outcome: string;
  price: number;
  stake: number;
  impliedProbability: number;
}

export interface ArbitrageOpportunity {
  id: string;
  gameId: string;
  sport: string;
  homeTeam: string;
  awayTeam: string;
  commenceTime: string;
  market: string;
  profitPercent: number;
  totalImpliedProbability: number;
  legs: ArbLeg[];
  detectedAt: string;
}

function americanToDecimal(american: number): number {
  if (american >= 100) return american / 100 + 1;
  return 100 / Math.abs(american) + 1;
}

function toDecimal(price: number): number {
  if (price > 1 && price < 100 && price !== Math.floor(price)) return price;
  if (price >= 100 || price <= -100) return americanToDecimal(price);
  if (price > 1) return price;
  return americanToDecimal(price);
}

function impliedProb(decOdds: number): number {
  return 1 / decOdds;
}

function calculateOptimalStakes(legs: Array<{ decimalOdds: number }>, bankroll = 1000): number[] {
  const implied = legs.map((l) => 1 / l.decimalOdds);
  const totalImplied = implied.reduce((a, b) => a + b, 0);
  return implied.map((imp) => (bankroll * imp) / totalImplied);
}

export interface SportSummary {
  sport: string;
  count: number;
  avgProfit: number;
}

export interface MarketSummary {
  market: string;
  count: number;
}

export interface OpportunitiesSummary {
  totalOpportunities: number;
  averageProfitPercent: number;
  bestProfitPercent: number;
  sportBreakdown: SportSummary[];
  marketBreakdown: MarketSummary[];
}

export function findArbitrageOpportunities(
  games: OJGame[],
  marketFilter?: string
): ArbitrageOpportunity[] {
  const opportunities: ArbitrageOpportunity[] = [];
  const now = new Date().toISOString();

  for (const game of games) {
    const marketMap = new Map<
      string,
      Map<string, Array<{ bookmaker: string; bookmakerTitle: string; price: number }>>
    >();

    for (const bookmaker of game.bookmakers) {
      for (const market of bookmaker.markets) {
        if (marketFilter && market.key !== marketFilter) continue;

        const marketKey = market.outcomes.some((o) => o.point !== undefined)
          ? `${market.key}_${market.outcomes[0]?.point ?? ""}`
          : market.key;

        if (!marketMap.has(marketKey)) marketMap.set(marketKey, new Map());
        const outcomeMap = marketMap.get(marketKey)!;

        for (const outcome of market.outcomes) {
          const ptStr = outcome.point !== undefined
            ? `${outcome.point > 0 ? "+" : ""}${outcome.point}`
            : "";
          const outcomeName = (ptStr && !outcome.name.includes(ptStr))
            ? `${outcome.name} ${ptStr}`
            : outcome.name;

          if (!outcomeMap.has(outcomeName)) outcomeMap.set(outcomeName, []);
          outcomeMap.get(outcomeName)!.push({
            bookmaker: bookmaker.key,
            bookmakerTitle: bookmaker.title,
            price: outcome.price,
          });
        }
      }
    }

    for (const [marketKey, outcomeMap] of marketMap) {
      const outcomes = Array.from(outcomeMap.entries());
      if (outcomes.length < 2 || outcomes.length > 3) continue;

      const bestLegs = outcomes.map(([outcomeName, bets]) => {
        let best = bets[0]!;
        for (const b of bets) {
          if (toDecimal(b.price) > toDecimal(best.price)) best = b;
        }
        return {
          outcome: outcomeName,
          bookmaker: best.bookmaker,
          bookmakerTitle: best.bookmakerTitle,
          price: best.price,
          decimalOdds: toDecimal(best.price),
        };
      });

      const totalImplied = bestLegs.reduce((sum, leg) => sum + impliedProb(leg.decimalOdds), 0);

      if (totalImplied < 1) {
        const profitPercent = ((1 / totalImplied) - 1) * 100;
        const stakes = calculateOptimalStakes(bestLegs, 1000);
        const baseMkt = marketKey.includes("_") ? marketKey.split("_")[0]! : marketKey;

        opportunities.push({
          id: `${game.id}_${marketKey}`,
          gameId: game.id,
          sport: game.sport_key,
          homeTeam: game.home_team,
          awayTeam: game.away_team,
          commenceTime: game.commence_time,
          market: baseMkt,
          profitPercent: Math.round(profitPercent * 1000) / 1000,
          totalImpliedProbability: Math.round(totalImplied * 10000) / 10000,
          legs: bestLegs.map((leg, i) => ({
            bookmaker: leg.bookmaker,
            bookmakerTitle: leg.bookmakerTitle,
            outcome: leg.outcome,
            price: leg.price,
            stake: Math.round((stakes[i] ?? 0) * 100) / 100,
            impliedProbability: Math.round(impliedProb(leg.decimalOdds) * 10000) / 10000,
          })),
          detectedAt: now,
        });
      }
    }
  }

  return opportunities.sort((a, b) => b.profitPercent - a.profitPercent);
}

export function computeSummary(opportunities: ArbitrageOpportunity[]): OpportunitiesSummary {
  const sportMap = new Map<string, { count: number; totalProfit: number }>();
  const marketMap = new Map<string, number>();

  for (const opp of opportunities) {
    const s = sportMap.get(opp.sport) ?? { count: 0, totalProfit: 0 };
    s.count++;
    s.totalProfit += opp.profitPercent;
    sportMap.set(opp.sport, s);
    marketMap.set(opp.market, (marketMap.get(opp.market) ?? 0) + 1);
  }

  return {
    totalOpportunities: opportunities.length,
    averageProfitPercent:
      opportunities.length > 0
        ? Math.round((opportunities.reduce((s, o) => s + o.profitPercent, 0) / opportunities.length) * 1000) / 1000
        : 0,
    bestProfitPercent: opportunities.length > 0 ? opportunities[0]!.profitPercent : 0,
    sportBreakdown: Array.from(sportMap.entries()).map(([sport, v]) => ({
      sport,
      count: v.count,
      avgProfit: Math.round((v.totalProfit / v.count) * 1000) / 1000,
    })),
    marketBreakdown: Array.from(marketMap.entries()).map(([market, count]) => ({ market, count })),
  };
}
