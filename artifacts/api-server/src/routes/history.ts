import { Router, type IRouter } from "express";
import { buildHistoryChart } from "../lib/history-chart";
import { listHistory } from "../lib/opportunity-history";
import { getOpportunities } from "../lib/scanner";

const router: IRouter = Router();

router.get("/history/chart", async (req, res): Promise<void> => {
  const range = String(req.query.range ?? "today");
  const sport = String(req.query.sport ?? "all");
  const league = String(req.query.league ?? "all");

  if (!["today", "7d", "30d"].includes(range)) {
    res.status(400).json({ error: "range must be today, 7d, or 30d" });
    return;
  }

  try {
    await getOpportunities({ refresh: false }).catch(() => []);
    const payload = buildHistoryChart(range, sport, league, listHistory());
    res.json(payload);
  } catch (e) {
    req.log.error({ err: e }, "Failed to build history chart");
    res.status(500).json({ error: "Failed to fetch history" });
  }
});

export default router;
