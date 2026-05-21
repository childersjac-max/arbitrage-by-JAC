import { Router, type IRouter } from "express";

export interface AlertRule {
  id: string;
  minProfitPercent: number;
  sport?: string;
  market?: string;
  createdAt: string;
}

const alerts = new Map<string, AlertRule>();
let nextId = 1;

const router: IRouter = Router();

router.get("/alerts", (_req, res) => {
  res.json([...alerts.values()].sort((a, b) => b.createdAt.localeCompare(a.createdAt)));
});

router.post("/alerts", (req, res) => {
  const body = req.body as {
    minProfitPercent?: number;
    sport?: string;
    market?: string;
  };
  const minProfitPercent = Number(body.minProfitPercent ?? 1);
  if (Number.isNaN(minProfitPercent) || minProfitPercent <= 0) {
    res.status(400).json({ error: "minProfitPercent must be a positive number" });
    return;
  }
  const id = String(nextId++);
  const rule: AlertRule = {
    id,
    minProfitPercent,
    sport: body.sport,
    market: body.market,
    createdAt: new Date().toISOString(),
  };
  alerts.set(id, rule);
  res.status(201).json(rule);
});

router.delete("/alerts/:id", (req, res) => {
  const id = req.params.id;
  if (!id || !alerts.has(id)) {
    res.status(404).json({ error: "Alert not found" });
    return;
  }
  alerts.delete(id);
  res.status(204).send();
});

export default router;
