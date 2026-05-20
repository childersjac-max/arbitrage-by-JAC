import { Router, type IRouter } from "express";
import { getOdds, OddsJamError } from "../lib/oddsjam";

const router: IRouter = Router();

router.get("/odds", async (req, res): Promise<void> => {
  const sport = String(req.query.sport ?? "baseball");
  const league = req.query.league ? String(req.query.league) : undefined;
  const markets = req.query.market
    ? String(req.query.market)
    : req.query.markets
      ? String(req.query.markets)
      : undefined;

  try {
    const games = await getOdds({ sport, league, markets });
    res.json(games);
  } catch (e) {
    req.log.error({ err: e }, "Failed to fetch odds");
    if (e instanceof OddsJamError) {
      res.status(e.status >= 400 ? e.status : 502).json({ error: e.message });
      return;
    }
    if (e instanceof Error && e.message.includes("ODDSJAM_API_KEY")) {
      res.status(503).json({ error: "OddsJam API key not configured" });
      return;
    }
    res.status(500).json({ error: "Failed to fetch odds" });
  }
});

export default router;
