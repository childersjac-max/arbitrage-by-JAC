import { Router, type IRouter } from "express";

const router: IRouter = Router();

router.get("/config", (_req, res) => {
  res.json({
    configured: !!process.env["ODDSJAM_API_KEY"],
    ntfyEnabled: !!process.env["NTFY_TOPIC"],
  });
});

export default router;
