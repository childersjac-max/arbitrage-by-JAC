import { Router, type IRouter } from "express";
import { sendTestAlert } from "../lib/monitor";

const router: IRouter = Router();

router.post("/monitor/test", async (_req, res): Promise<void> => {
  const result = await sendTestAlert();
  if (!result.sent) {
    res.status(400).json({
      error: "NTFY_TOPIC environment variable is not set. Set it to enable phone alerts.",
      setup: "https://ntfy.sh — install the free app, subscribe to any topic name, then set NTFY_TOPIC=<your-topic>",
    });
    return;
  }
  res.json({ sent: true, topic: result.topic });
});

router.get("/monitor/status", (_req, res): void => {
  const topic = process.env["NTFY_TOPIC"] ?? null;
  res.json({
    enabled: !!topic,
    topic: topic ? `${topic.slice(0, 4)}****` : null,
    minProfitPct: 1.0,
    pollIntervalSeconds: 60,
    ntfyUrl: topic ? `https://ntfy.sh/${topic}` : null,
  });
});

export default router;
