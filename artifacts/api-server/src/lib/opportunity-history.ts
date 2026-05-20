import type { ArbitrageOpportunity } from "./arbitrage";

export interface HistoryRecord {
  oppId: string;
  sport: string;
  league: string | null;
  homeTeam: string;
  awayTeam: string;
  market: string;
  profitPercent: number;
  legs: ArbitrageOpportunity["legs"];
  firstSeenAt: string;
  lastSeenAt: string;
  durationMinutes: number;
}

const store = new Map<string, HistoryRecord>();

export function recordOpportunities(opportunities: ArbitrageOpportunity[]): void {
  const now = new Date().toISOString();
  for (const o of opportunities) {
    const existing = store.get(o.id);
    if (existing) {
      existing.lastSeenAt = now;
      existing.profitPercent = o.profitPercent;
      existing.legs = o.legs;
      existing.durationMinutes = Math.max(
        0,
        Math.round(
          (new Date(now).getTime() - new Date(existing.firstSeenAt).getTime()) /
            60000,
        ),
      );
    } else {
      store.set(o.id, {
        oppId: o.id,
        sport: o.sport,
        league: o.league ?? null,
        homeTeam: o.homeTeam,
        awayTeam: o.awayTeam,
        market: o.market,
        profitPercent: o.profitPercent,
        legs: o.legs,
        firstSeenAt: now,
        lastSeenAt: now,
        durationMinutes: 0,
      });
    }
  }
}

export function listHistory(): HistoryRecord[] {
  return [...store.values()];
}
