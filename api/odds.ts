import type { VercelRequest, VercelResponse } from "@vercel/node";
import { GetOddsQueryParams, GetOddsResponse } from "@workspace/api-zod";
import { getOdds, OddsJamError } from "@workspace/optic-odds";
import { setCors } from "./_lib/cors";

export default async function handler(req: VercelRequest, res: VercelResponse) {
  setCors(res);
  if (req.method === "OPTIONS") return res.status(204).end();
  if (req.method !== "GET") {
    return res.status(405).json({ error: "Method not allowed" });
  }

  const parsed = GetOddsQueryParams.safeParse(req.query);
  if (!parsed.success) {
    return res.status(400).json({ error: parsed.error.message });
  }

  const { sport, markets, bookmakers } = parsed.data;

  try {
    const raw = await getOdds({
      sport,
      markets: markets ?? undefined,
      bookmakers: bookmakers ?? undefined,
    });

    const games = raw.map((g) => ({
      id: g.id,
      sport: g.sport_key,
      homeTeam: g.home_team,
      awayTeam: g.away_team,
      commenceTime: g.commence_time,
      bookmakerOdds: g.bookmakers.flatMap((bm) =>
        bm.markets.flatMap((mkt) =>
          mkt.outcomes.map((outcome) => ({
            bookmaker: bm.key,
            bookmakerTitle: bm.title,
            market: mkt.key,
            outcome: outcome.name,
            price: outcome.price,
            point: outcome.point ?? null,
            lastUpdate: mkt.last_update,
          })),
        ),
      ),
    }));

    return res.status(200).json(GetOddsResponse.parse(games));
  } catch (err) {
    if (err instanceof OddsJamError) {
      return res.status(502).json({ error: `Optic Odds API error: ${err.body}` });
    }
    throw err;
  }
}
