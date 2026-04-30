import { Router, type IRouter } from "express";
import { db, alertsTable } from "@workspace/db";
import { eq } from "drizzle-orm";
import {
  GetAlertsResponse,
  CreateAlertBody,
  DeleteAlertParams,
} from "@workspace/api-zod";

const router: IRouter = Router();

router.get("/alerts", async (req, res): Promise<void> => {
  const alerts = await db.select().from(alertsTable).orderBy(alertsTable.createdAt);
  const mapped = alerts.map((a) => ({
    id: a.id,
    sport: a.sport ?? null,
    market: a.market ?? null,
    minProfitPercent: parseFloat(a.minProfitPercent),
    createdAt: a.createdAt.toISOString(),
  }));
  res.json(GetAlertsResponse.parse(mapped));
});

router.post("/alerts", async (req, res): Promise<void> => {
  const parsed = CreateAlertBody.safeParse(req.body);
  if (!parsed.success) {
    res.status(400).json({ error: parsed.error.message });
    return;
  }

  const { sport, market, minProfitPercent } = parsed.data;

  const [alert] = await db
    .insert(alertsTable)
    .values({
      sport: sport ?? null,
      market: market ?? null,
      minProfitPercent: String(minProfitPercent ?? 0),
    })
    .returning();

  if (!alert) {
    res.status(500).json({ error: "Failed to create alert" });
    return;
  }

  res.status(201).json({
    id: alert.id,
    sport: alert.sport ?? null,
    market: alert.market ?? null,
    minProfitPercent: parseFloat(alert.minProfitPercent),
    createdAt: alert.createdAt.toISOString(),
  });
});

router.delete("/alerts/:id", async (req, res): Promise<void> => {
  const params = DeleteAlertParams.safeParse(req.params);
  if (!params.success) {
    res.status(400).json({ error: params.error.message });
    return;
  }

  const [deleted] = await db
    .delete(alertsTable)
    .where(eq(alertsTable.id, params.data.id))
    .returning();

  if (!deleted) {
    res.status(404).json({ error: "Alert not found" });
    return;
  }

  res.sendStatus(204);
});

export default router;
