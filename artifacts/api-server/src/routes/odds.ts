import { Router, type IRouter } from "express";
import { getOdds, OddsJamError } from "../lib/oddsjam";
import { GetOddsQueryParams, GetOddsResponse } from "@workspace/api-zod";

const router: IRouter = Router();

router.get("/odds", async (req, res): Promise<void> => {
  const parsed = GetOddsQueryParams.safeParse(req.query);
  if (!parsed.success) {
    res.status(400).json({ error: parsed.error.message });
    return;
  }

  const { sport, markets, bookmakers } = parsed.data;

  try {
    const raw = await getOdds({
      sport,
      markets: markets ?? undefined,
      bookmakers: bookmakers ?? undefined,
    });

    const games = raw.map((g) => ({
      id: g.id,
      sport: g.sport_key,
      homeTeam: g.home_team,
      awayTeam: g.away_team,
      commenceTime: g.commence_time,
      bookmakerOdds: g.bookmakers.flatMap((bm) =>
        bm.markets.flatMap((mkt) =>
          mkt.outcomes.map((outcome) => ({
            bookmaker: bm.key,
            bookmakerTitle: bm.title,
            market: mkt.key,
            outcome: outcome.name,
            price: outcome.price,
            point: outcome.point ?? null,
            lastUpdate: mkt.last_update,
          }))
        )
      ),
    }));

    res.json(GetOddsResponse.parse(games));
  } catch (err) {
    if (err instanceof OddsJamError) {
      req.log.error({ status: err.status }, "OddsJam error fetching odds");
      res.status(502).json({ error: `OddsJam API error: ${err.body}` });
      return;
    }
    throw err;
  }
});

export default router;
