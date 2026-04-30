import { Router, type IRouter } from "express";
import { getSports, OddsJamError } from "../lib/oddsjam";
import { GetSportsResponse } from "@workspace/api-zod";

const router: IRouter = Router();

router.get("/sports", async (req, res): Promise<void> => {
  try {
    const raw = await getSports();
    const sports = raw.map((s) => ({
      key: s.key,
      group: s.group,
      title: s.title,
      description: s.description,
      active: s.active,
      hasOutrights: s.has_outrights,
    }));
    res.json(GetSportsResponse.parse(sports));
  } catch (err) {
    if (err instanceof OddsJamError) {
      req.log.error({ status: err.status }, "OddsJam error fetching sports");
      res.status(502).json({ error: `OddsJam API error: ${err.body}` });
      return;
    }
    throw err;
  }
});

export default router;
