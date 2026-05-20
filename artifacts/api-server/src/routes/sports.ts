import { Router, type IRouter } from "express";
import { getSports, OddsJamError } from "../lib/oddsjam";

const router: IRouter = Router();

router.get("/sports", async (req, res): Promise<void> => {
  try {
    const sports = await getSports();
    res.json(
      sports.map((s) => ({
        key: s.key,
        group: s.group,
        title: s.title,
        description: s.description,
        active: s.active,
        hasOutrights: s.has_outrights,
      })),
    );
  } catch (e) {
    req.log.error({ err: e }, "Failed to fetch sports");
    if (e instanceof OddsJamError) {
      res.status(e.status >= 400 ? e.status : 502).json({ error: e.message });
      return;
    }
    res.status(500).json({ error: "Failed to fetch sports" });
  }
});

export default router;
