import type { VercelRequest, VercelResponse } from "@vercel/node";
import { setCors } from "./_lib/cors";

export default function handler(req: VercelRequest, res: VercelResponse) {
  setCors(res);
  if (req.method === "OPTIONS") return res.status(204).end();
  if (req.method !== "GET") {
    return res.status(405).json({ error: "Method not allowed" });
  }

  return res.status(200).json({ status: "ok" });
}
