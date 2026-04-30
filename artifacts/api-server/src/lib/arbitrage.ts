import type { OJGame } from "./oddsjam";

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

function impliedProbability(decimalOdds: number): number {
  return 1 / decimalOdds;
}

function calculateStakes(
  legs: Array<{ decimalOdds: number }>,
  totalBankroll = 1000
): number[] {
  // Kelly-style equal-profit stake calculation
  const totalImplied = legs.reduce((s, l) => s + 1 / l.decimalOdds, 0);
  return legs.map((l) => (totalBankroll / l.decimalOdds) / totalImplied * totalImplied / legs.length * (1 / l.decimalOdds / totalImplied) * totalBankroll);
}

function calculateOptimalStakes(legs: Array<{ decimalOdds: number }>, bankroll = 1000): number[] {
  // For guaranteed profit: stake_i = bankroll * (1/odds_i) / sum(1/odds_j)
  // This ensures equal profit regardless of which outcome wins
  const implied = legs.map((l) => 1 / l.decimalOdds);
  const totalImplied = implied.reduce((a, b) => a + b, 0);
  return implied.map((imp) => (bankroll * imp) / totalImplied);
}

export function findArbitrageOpportunities(
  games: OJGame[],
  marketFilter?: string
): ArbitrageOpportunity[] {
  const opportunities: ArbitrageOpportunity[] = [];
  const now = new Date().toISOString();

  for (const game of games) {
    // Collect all markets to analyze
    const marketMap = new Map<
      string,
      Map<string, Array<{ bookmaker: string; bookmakerTitle: string; price: number; point?: number }>>
    >();

    for (const bookmaker of game.bookmakers) {
      for (const market of bookmaker.markets) {
        if (marketFilter && market.key !== marketFilter) continue;

        // For totals/spreads, group by market+point to compare same lines
        const marketKey = market.outcomes.some((o) => o.point !== undefined)
          ? `${market.key}_${market.outcomes[0]?.point ?? ""}`
          : market.key;

        if (!marketMap.has(marketKey)) {
          marketMap.set(marketKey, new Map());
        }
        const outcomeMap = marketMap.get(marketKey)!;

        for (const outcome of market.outcomes) {
          const outcomeName = outcome.point !== undefined
            ? `${outcome.name} ${outcome.point > 0 ? "+" : ""}${outcome.point}`
            : outcome.name;

          if (!outcomeMap.has(outcomeName)) {
            outcomeMap.set(outcomeName, []);
          }
          outcomeMap.get(outcomeName)!.push({
            bookmaker: bookmaker.key,
            bookmakerTitle: bookmaker.title,
            price: outcome.price,
          });
        }
      }
    }

    // For each market group, find the best odds for each outcome
    for (const [marketKey, outcomeMap] of marketMap) {
      const outcomes = Array.from(outcomeMap.entries());

      // Only analyze markets with 2 or 3 outcomes (moneyline, spread, totals)
      if (outcomes.length < 2 || outcomes.length > 3) continue;

      // Find best (highest decimal) odds for each outcome
      const bestLegs = outcomes.map(([outcomeName, bets]) => {
        let best = bets[0]!;
        for (const b of bets) {
          const decB = b.price >= 100 || b.price <= -100 ? americanToDecimal(b.price) : b.price;
          const decBest = best.price >= 100 || best.price <= -100 ? americanToDecimal(best.price) : best.price;
          if (decB > decBest) best = b;
        }
        const decimalOdds = best.price >= 100 || best.price <= -100
          ? americanToDecimal(best.price)
          : best.price > 1 ? best.price : americanToDecimal(best.price);
        return {
          outcome: outcomeName,
          bookmaker: best.bookmaker,
          bookmakerTitle: best.bookmakerTitle,
          price: best.price,
          decimalOdds,
        };
      });

      // Calculate total implied probability
      const totalImplied = bestLegs.reduce(
        (sum, leg) => sum + impliedProbability(leg.decimalOdds),
        0
      );

      // Arbitrage exists when totalImplied < 1
      if (totalImplied < 1) {
        const profitPercent = ((1 / totalImplied) - 1) * 100;
        const bankroll = 1000;
        const stakes = calculateOptimalStakes(bestLegs, bankroll);

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
            impliedProbability: Math.round(impliedProbability(leg.decimalOdds) * 10000) / 10000,
          })),
          detectedAt: now,
        });
      }
    }
  }

  return opportunities.sort((a, b) => b.profitPercent - a.profitPercent);
}
