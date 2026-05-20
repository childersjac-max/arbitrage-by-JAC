import { db } from "@workspace/db";
import { arbHistoryTable } from "@workspace/db/schema";
import { and, eq, gte, lte } from "drizzle-orm";
import type { ArbitrageOpportunity } from "./arbitrage";
import type { HistoryRecord } from "./history-chart";

function rowToRecord(row: typeof arbHistoryTable.$inferSelect): HistoryRecord {
  return {
    oppId: row.oppId,
    sport: row.sport,
    league: row.league,
    homeTeam: row.homeTeam,
    awayTeam: row.awayTeam,
    market: row.market,
    profitPercent: row.profitPercent,
    firstSeenAt: row.firstSeenAt.toISOString(),
    lastSeenAt: row.lastSeenAt.toISOString(),
    durationMinutes: row.durationMinutes,
    legs: row.legs as HistoryRecord["legs"],
  };
}

export async function recordOpportunitiesToDb(
  opportunities: ArbitrageOpportunity[],
): Promise<void> {
  if (!db) return;
  const now = new Date();
  for (const o of opportunities) {
    const existing = await db
      .select()
      .from(arbHistoryTable)
      .where(eq(arbHistoryTable.oppId, o.id))
      .limit(1);

    if (existing.length > 0) {
      const row = existing[0]!;
      await db
        .update(arbHistoryTable)
        .set({
          profitPercent: o.profitPercent,
          legs: o.legs,
          lastSeenAt: now,
          durationMinutes: Math.max(
            0,
            Math.round((now.getTime() - row.firstSeenAt.getTime()) / 60000),
          ),
          league: o.league ?? row.league,
        })
        .where(eq(arbHistoryTable.oppId, o.id));
    } else {
      await db.insert(arbHistoryTable).values({
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

export async function listHistoryFromDb(
  since: Date,
  until: Date,
): Promise<HistoryRecord[]> {
  if (!db) return [];
  const rows = await db
    .select()
    .from(arbHistoryTable)
    .where(
      and(
        gte(arbHistoryTable.firstSeenAt, since),
        lte(arbHistoryTable.firstSeenAt, until),
      ),
    );
  return rows.map(rowToRecord);
}
