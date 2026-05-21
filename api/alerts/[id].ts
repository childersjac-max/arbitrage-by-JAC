import type { VercelRequest, VercelResponse } from "@vercel/node";
import { db, alertsTable } from "@workspace/db";
import { DeleteAlertParams } from "@workspace/api-zod";
import { eq } from "drizzle-orm";
import { setCors } from "../_lib/cors";

export default async function handler(req: VercelRequest, res: VercelResponse) {
  setCors(res);
  if (req.method === "OPTIONS") return res.status(204).end();
  if (req.method !== "DELETE") {
    res.setHeader("Allow", "DELETE, OPTIONS");
    return res.status(405).json({ error: "Method not allowed" });
  }

  const params = DeleteAlertParams.safeParse(req.query);
  if (!params.success) {
    return res.status(400).json({ error: params.error.message });
  }

  try {
    const [deleted] = await db
      .delete(alertsTable)
      .where(eq(alertsTable.id, params.data.id))
      .returning();

    if (!deleted) {
      return res.status(404).json({ error: "Alert not found" });
    }

    return res.status(204).end();
  } catch (err) {
    const message = err instanceof Error ? err.message : "Database error";
    if (message.includes("DATABASE_URL")) {
      return res.status(503).json({ error: "Alerts database not configured" });
    }
    throw err;
  }
}
