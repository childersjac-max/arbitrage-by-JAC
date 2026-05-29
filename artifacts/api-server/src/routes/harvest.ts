import { Router, type IRouter } from "express";
import { isArbHarvestAvailable, runArbHarvest } from "../lib/arb-harvest-runner";

const router: IRouter = Router();

router.get("/harvest/health", (_req, res): void => {
  res.json({
    available: isArbHarvestAvailable(),
    oddsApiKeySet: Boolean(process.env["ODDS_API_KEY"]),
  });
});

router.get("/harvest", async (req, res): Promise<void> => {
  try {
    const refresh = req.query.refresh === "1" || req.query.refresh === "true";
    const payload = await runArbHarvest({ refresh });
    res.json(payload);
  } catch (e) {
    req.log.error({ err: e }, "harvest failed");
    res.status(500).json({ error: "Harvest failed", detail: String(e) });
  }
});

router.get("/harvest/signals", async (req, res): Promise<void> => {
  try {
    const refresh = req.query.refresh === "1" || req.query.refresh === "true";
    const payload = await runArbHarvest({ refresh });
    const signals = payload["arbitrage_signals"];
    res.json(Array.isArray(signals) ? signals : []);
  } catch (e) {
    req.log.error({ err: e }, "harvest signals failed");
    res.status(500).json({ error: "Harvest signals failed" });
  }
});

export default router;
