/**
 * Example: wire history-chart into production history route (reads arb_history).
 * Adjust table/column names to match lib/db/src/schema arb_history.
 */
import { Router } from "express";
import { db } from "@workspace/db";
import { arbHistoryTable } from "@workspace/db/schema"; // your actual export
import { buildHistoryChart } from "../lib/history-chart";
import { gte, lte, and } from "drizzle-orm";

const router = Router();

router.get("/history/chart", async (req, res) => {
  const range = String(req.query.range ?? "today");
  const sport = String(req.query.sport ?? "all");
  const league = String(req.query.league ?? "all");

  const win = /* same since/until as buildHistoryChart rangeWindow, or query after build */;
  const rows = await db
    .select()
    .from(arbHistoryTable)
    .where(
      and(
        gte(arbHistoryTable.firstSeenAt, win.since),
        lte(arbHistoryTable.firstSeenAt, win.until),
      ),
    );

  const records = rows.map((r) => ({
    oppId: r.oppId,
    sport: r.sport,
    league: r.league,
    homeTeam: r.homeTeam,
    awayTeam: r.awayTeam,
    market: r.market,
    profitPercent: r.profitPercent,
    firstSeenAt: r.firstSeenAt.toISOString(),
    lastSeenAt: r.lastSeenAt.toISOString(),
    durationMinutes: r.durationMinutes,
    legs: r.legs,
  }));

  res.json(buildHistoryChart(range, sport, league, records));
});

export default router;
