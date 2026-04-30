import { Router, type IRouter } from "express";
import { getOdds, getSports, OddsJamError } from "../lib/oddsjam";
import { findArbitrageOpportunities } from "../lib/arbitrage";
import {
  GetArbitrageOpportunitiesQueryParams,
  GetArbitrageOpportunitiesResponse,
  GetOpportunitiesSummaryResponse,
} from "@workspace/api-zod";

const router: IRouter = Router();

const MAJOR_SPORTS = [
  "baseball",
  "basketball",
  "football",
  "hockey",
  "soccer",
  "tennis",
  "mma",
];

async function fetchOpportunities(params: {
  sport?: string | null;
  minProfit?: number | null;
  market?: string | null;
}) {
  let sports: string[];

  if (params.sport) {
    sports = [params.sport];
  } else {
    // Fetch all active sports and use major ones or first 6
    try {
      const allSports = await getSports();
      const activeSports = allSports.filter((s) => s.active);
      const major = activeSports.filter((s) => MAJOR_SPORTS.includes(s.key));
      sports = major.length > 0 ? major.map((s) => s.key) : activeSports.slice(0, 6).map((s) => s.key);
    } catch {
      sports = MAJOR_SPORTS;
    }
  }

  const allOpportunities = [];

  for (const sport of sports) {
    try {
      const games = await getOdds({ sport });
      const opps = findArbitrageOpportunities(games, params.market ?? undefined);
      allOpportunities.push(...opps);
    } catch {
      // Skip failed sports silently
    }
  }

  const minProfit = params.minProfit ?? 0;
  return allOpportunities
    .filter((o) => o.profitPercent >= minProfit)
    .sort((a, b) => b.profitPercent - a.profitPercent);
}

router.get("/opportunities", async (req, res): Promise<void> => {
  const parsed = GetArbitrageOpportunitiesQueryParams.safeParse(req.query);
  if (!parsed.success) {
    res.status(400).json({ error: parsed.error.message });
    return;
  }

  try {
    const opportunities = await fetchOpportunities(parsed.data);
    res.json(GetArbitrageOpportunitiesResponse.parse(opportunities));
  } catch (err) {
    if (err instanceof OddsJamError) {
      req.log.error({ status: err.status }, "OddsJam error fetching opportunities");
      res.status(502).json({ error: `OddsJam API error: ${err.body}` });
      return;
    }
    throw err;
  }
});

router.get("/opportunities/summary", async (req, res): Promise<void> => {
  try {
    const opportunities = await fetchOpportunities({});

    const sportBreakdownMap = new Map<string, { count: number; totalProfit: number }>();
    const marketBreakdownMap = new Map<string, number>();

    for (const opp of opportunities) {
      const s = sportBreakdownMap.get(opp.sport) ?? { count: 0, totalProfit: 0 };
      s.count++;
      s.totalProfit += opp.profitPercent;
      sportBreakdownMap.set(opp.sport, s);

      marketBreakdownMap.set(opp.market, (marketBreakdownMap.get(opp.market) ?? 0) + 1);
    }

    const summary = {
      totalOpportunities: opportunities.length,
      averageProfitPercent:
        opportunities.length > 0
          ? Math.round((opportunities.reduce((s, o) => s + o.profitPercent, 0) / opportunities.length) * 1000) / 1000
          : 0,
      bestProfitPercent: opportunities.length > 0 ? opportunities[0]!.profitPercent : 0,
      sportBreakdown: Array.from(sportBreakdownMap.entries()).map(([sport, v]) => ({
        sport,
        count: v.count,
        avgProfit: Math.round((v.totalProfit / v.count) * 1000) / 1000,
      })),
      marketBreakdown: Array.from(marketBreakdownMap.entries()).map(([market, count]) => ({
        market,
        count,
      })),
    };

    res.json(GetOpportunitiesSummaryResponse.parse(summary));
  } catch (err) {
    if (err instanceof OddsJamError) {
      req.log.error({ status: err.status }, "OddsJam error fetching summary");
      res.status(502).json({ error: `OddsJam API error: ${err.body}` });
      return;
    }
    throw err;
  }
});

export default router;
