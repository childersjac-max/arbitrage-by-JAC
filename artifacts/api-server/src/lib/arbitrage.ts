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
  league?: string;
  homeTeam: string;
  awayTeam: string;
  commenceTime: string;
  market: string;
  profitPercent: number;
  totalImpliedProbability: number;
  legs: ArbLeg[];
  detectedAt: string;
}

// American odds must be ≥ +100 or ≤ -100. Values in [-99, 99] are invalid.
function isValidAmericanOdds(price: number): boolean {
  return price >= 100 || price <= -100;
}

function americanToDecimal(american: number): number {
  if (american >= 100) return american / 100 + 1;
  return 100 / Math.abs(american) + 1;
}

function impliedProbability(decimalOdds: number): number {
  return 1 / decimalOdds;
}

// stake_i = bankroll × (1/odds_i) / Σ(1/odds_j)
// Guarantees equal absolute profit regardless of which outcome wins.
function calculateOptimalStakes(legs: Array<{ decimalOdds: number }>, bankroll = 1000): number[] {
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
      Map<string, Array<{ bookmaker: string; bookmakerTitle: string; price: number }>>
    >();

    for (const bookmaker of game.bookmakers) {
      for (const market of bookmaker.markets) {
        if (marketFilter && market.key !== marketFilter) continue;

        // Group by market key + line value so we only compare like-for-like
        const marketKey = market.outcomes.some((o) => o.point !== undefined)
          ? `${market.key}_${market.outcomes[0]?.point ?? ""}`
          : market.key;

        if (!marketMap.has(marketKey)) {
          marketMap.set(marketKey, new Map());
        }
        const outcomeMap = marketMap.get(marketKey)!;

        for (const outcome of market.outcomes) {
          // Reject any price that is not valid American odds
          if (!isValidAmericanOdds(outcome.price)) continue;

          // Normalize outcome name to a canonical form so the same prop line
          // matches across books regardless of how they embed the point value.
          // e.g. "Over 11.5", "Over +11.5", "Over" (point:11.5) → "Over +11.5"
          const ptStr = outcome.point !== undefined
            ? `${outcome.point > 0 ? "+" : ""}${outcome.point}`
            : "";
          let baseName = outcome.name.trim();
          if (outcome.point !== undefined) {
            const absStr = Math.abs(outcome.point).toString().replace(".", "\\.");
            baseName = baseName
              .replace(new RegExp(`\\s+[+-]?${absStr}\\s*$`), "")
              .trim();
          }
          const outcomeName = ptStr ? `${baseName} ${ptStr}` : baseName;

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

      // Only analyze markets with exactly 2 or 3 mutually exclusive outcomes
      if (outcomes.length < 2 || outcomes.length > 3) continue;

      // Find best (highest decimal) odds for each outcome across all sportsbooks
      const bestLegs = outcomes.map(([outcomeName, bets]) => {
        let best = bets[0]!;
        for (const b of bets) {
          if (americanToDecimal(b.price) > americanToDecimal(best.price)) best = b;
        }
        return {
          outcome: outcomeName,
          bookmaker: best.bookmaker,
          bookmakerTitle: best.bookmakerTitle,
          price: best.price,
          decimalOdds: americanToDecimal(best.price),
        };
      });

      // ── REAL-ARB GUARD ────────────────────────────────────────────────────
      // All legs must be at distinct sportsbooks. If the same book appears on
      // every leg it means one book is offering all sides — that is not an
      // executable cross-book arbitrage regardless of the math.
      const uniqueBooks = new Set(bestLegs.map((l) => l.bookmaker));
      if (uniqueBooks.size < 2) continue;

      // Each leg's decimal odds must be > 1 (sanity check)
      if (bestLegs.some((l) => l.decimalOdds <= 1)) continue;
      // ─────────────────────────────────────────────────────────────────────

      // Calculate total implied probability
      const totalImplied = bestLegs.reduce(
        (sum, leg) => sum + impliedProbability(leg.decimalOdds),
        0
      );

      // True arbitrage: totalImplied strictly < 1.0
      if (totalImplied < 1) {
        const profitPercent = ((1 / totalImplied) - 1) * 100;
        const bankroll = 100;
        const stakes = calculateOptimalStakes(bestLegs, bankroll);

        const baseMkt = marketKey.includes("::") ? marketKey.split("::")[0]! : marketKey;

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
