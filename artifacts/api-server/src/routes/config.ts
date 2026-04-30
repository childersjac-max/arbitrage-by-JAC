import { Router, type IRouter } from "express";

const router: IRouter = Router();

router.get("/config", async (req, res): Promise<void> => {
  const apiKey = process.env["ODDSJAM_API_KEY"];
  if (!apiKey) {
    req.log.warn("ODDSJAM_API_KEY is not configured");
    res.status(503).json({ error: "OddsJam API key not configured" });
    return;
  }
  res.json({ oddsjamApiKey: apiKey });
});

export default router;
