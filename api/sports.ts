import type { VercelRequest, VercelResponse } from "@vercel/node";
import { GetSportsResponse } from "@workspace/api-zod";
import { getSports, OddsJamError } from "@workspace/optic-odds";
import { setCors } from "./_lib/cors";

export default async function handler(req: VercelRequest, res: VercelResponse) {
  setCors(res);
  if (req.method === "OPTIONS") return res.status(204).end();
  if (req.method !== "GET") {
    return res.status(405).json({ error: "Method not allowed" });
  }

  try {
    const raw = await getSports();
    const sports = raw.map((s) => ({
      key: s.key,
      group: s.group,
      title: s.title,
      description: s.description,
      active: s.active,
      hasOutrights: s.has_outrights,
    }));
    return res.status(200).json(GetSportsResponse.parse(sports));
  } catch (err) {
    if (err instanceof OddsJamError) {
      return res.status(502).json({ error: `Optic Odds API error: ${err.body}` });
    }
    throw err;
  }
}
