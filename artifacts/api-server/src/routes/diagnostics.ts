import { Router, type IRouter } from "express";
import { SCAN_TARGETS } from "../lib/scan-config";

const router: IRouter = Router();

router.get("/diagnostics", (_req, res) => {
  res.json({
    oddsjamConfigured: !!process.env["ODDSJAM_API_KEY"],
    databaseConfigured: !!process.env["DATABASE_URL"],
    ntfyTopic: process.env["NTFY_TOPIC"] ? "set" : null,
    scanTargets: SCAN_TARGETS,
  });
});

export default router;
