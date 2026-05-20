import { Router, type IRouter } from "express";
import { getTrackedGames } from "../lib/tracked-games";

const router: IRouter = Router();

router.get("/tracked-games", async (req, res): Promise<void> => {
  const sport = String(req.query.sport ?? "basketball");
  const markets = req.query.markets ? String(req.query.markets) : undefined;
  const days = req.query.days ? Number(req.query.days) : 3;

  try {
    const games = await getTrackedGames({ sport, markets, days });
    res.json(games);
  } catch (e) {
    req.log.error({ err: e }, "Failed to fetch tracked games");
    res.status(500).json({ error: "Failed to fetch tracked games" });
  }
});

export default router;
