import type { VercelRequest, VercelResponse } from "@vercel/node";
import { db, alertsTable } from "@workspace/db";
import { CreateAlertBody, GetAlertsResponse } from "@workspace/api-zod";
import { eq } from "drizzle-orm";
import { setCors } from "./_lib/cors";

function mapAlert(a: typeof alertsTable.$inferSelect) {
  return {
    id: a.id,
    sport: a.sport ?? null,
    market: a.market ?? null,
    minProfitPercent: parseFloat(a.minProfitPercent),
    createdAt: a.createdAt.toISOString(),
  };
}

export default async function handler(req: VercelRequest, res: VercelResponse) {
  setCors(res);
  if (req.method === "OPTIONS") return res.status(204).end();

  if (req.method === "GET") {
    try {
      const alerts = await db
        .select()
        .from(alertsTable)
        .orderBy(alertsTable.createdAt);
      return res.status(200).json(GetAlertsResponse.parse(alerts.map(mapAlert)));
    } catch (err) {
      const message = err instanceof Error ? err.message : "Database error";
      if (message.includes("DATABASE_URL")) {
        return res.status(503).json({ error: "Alerts database not configured" });
      }
      throw err;
    }
  }

  if (req.method === "POST") {
    const parsed = CreateAlertBody.safeParse(req.body);
    if (!parsed.success) {
      return res.status(400).json({ error: parsed.error.message });
    }

    const { sport, market, minProfitPercent } = parsed.data;

    try {
      const [alert] = await db
        .insert(alertsTable)
        .values({
          sport: sport ?? null,
          market: market ?? null,
          minProfitPercent: String(minProfitPercent ?? 0),
        })
        .returning();

      if (!alert) {
        return res.status(500).json({ error: "Failed to create alert" });
      }

      return res.status(201).json(mapAlert(alert));
    } catch (err) {
      const message = err instanceof Error ? err.message : "Database error";
      if (message.includes("DATABASE_URL")) {
        return res.status(503).json({ error: "Alerts database not configured" });
      }
      throw err;
    }
  }

  res.setHeader("Allow", "GET, POST, OPTIONS");
  return res.status(405).json({ error: "Method not allowed" });
}
