import { Router, type IRouter } from "express";
import { isCommenceTodayOrTomorrow } from "../lib/date-window";
import { getOpportunities, buildSummary } from "../lib/scanner";

const router: IRouter = Router();

function onlyTodayAndTomorrow<T extends { commenceTime: string }>(opps: T[]): T[] {
  return opps.filter((o) => isCommenceTodayOrTomorrow(o.commenceTime));
}

router.get("/opportunities", async (req, res): Promise<void> => {
  try {
    const refresh = req.query.refresh === "1" || req.query.refresh === "true";
    const opps = onlyTodayAndTomorrow(await getOpportunities({ refresh }));
    res.json(opps);
  } catch (e) {
    req.log.error({ err: e }, "Failed to fetch opportunities");
    res.status(500).json({ error: "Failed to fetch opportunities" });
  }
});

router.get("/opportunities/summary", async (req, res): Promise<void> => {
  try {
    const opps = onlyTodayAndTomorrow(await getOpportunities({ refresh: false }));
    res.json(buildSummary(opps));
  } catch (e) {
    req.log.error({ err: e }, "Failed to fetch summary");
    res.status(500).json({ error: "Failed to fetch summary" });
  }
});

export default router;
