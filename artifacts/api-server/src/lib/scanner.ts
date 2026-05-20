import { logger } from "./logger";
import { findArbitrageOpportunities, type ArbitrageOpportunity } from "./arbitrage";
import { getOdds, OddsJamError } from "./oddsjam";
import { recordOpportunities } from "./opportunity-history";
import { SCAN_TARGETS } from "./scan-config";

const CACHE_TTL_MS = 30_000;

let cached: ArbitrageOpportunity[] = [];
let cachedAt = 0;
let scanInFlight: Promise<ArbitrageOpportunity[]> | null = null;

async function runScan(): Promise<ArbitrageOpportunity[]> {
  if (!process.env["ODDSJAM_API_KEY"]) {
    return [];
  }

  const all: ArbitrageOpportunity[] = [];

  for (const target of SCAN_TARGETS) {
    for (const league of target.leagues) {
      try {
        const games = await getOdds({ sport: target.sport, league });
        const opps = findArbitrageOpportunities(games);
        for (const o of opps) {
          o.league = league;
          if (league === "wnba") o.sport = "basketball";
        }
        all.push(...opps);
      } catch (e) {
        if (e instanceof OddsJamError) {
          logger.warn(
            { sport: target.sport, league, status: e.status },
            "Scanner: league skipped",
          );
        }
      }
    }
  }

  const byId = new Map<string, ArbitrageOpportunity>();
  for (const o of all) {
    const prev = byId.get(o.id);
    if (!prev || o.profitPercent > prev.profitPercent) byId.set(o.id, o);
  }

  return [...byId.values()].sort((a, b) => b.profitPercent - a.profitPercent);
}

export async function getOpportunities(options?: {
  refresh?: boolean;
}): Promise<ArbitrageOpportunity[]> {
  const now = Date.now();
  if (
    !options?.refresh &&
    cached.length > 0 &&
    now - cachedAt < CACHE_TTL_MS
  ) {
    return cached;
  }

  if (scanInFlight) return scanInFlight;

  scanInFlight = (async () => {
    try {
      const opps = await runScan();
      cached = opps;
      cachedAt = Date.now();
      recordOpportunities(opps);
      return opps;
    } finally {
      scanInFlight = null;
    }
  })();

  return scanInFlight;
}

export function buildSummary(opportunities: ArbitrageOpportunity[]) {
  const sportMap = new Map<string, { count: number; profitSum: number }>();
  const marketMap = new Map<string, number>();

  for (const o of opportunities) {
    const sk = sportMap.get(o.sport) ?? { count: 0, profitSum: 0 };
    sk.count += 1;
    sk.profitSum += o.profitPercent;
    sportMap.set(o.sport, sk);
    marketMap.set(o.market, (marketMap.get(o.market) ?? 0) + 1);
  }

  const profitSum = opportunities.reduce((s, o) => s + o.profitPercent, 0);
  const best = opportunities.reduce(
    (m, o) => Math.max(m, o.profitPercent),
    0,
  );

  return {
    totalOpportunities: opportunities.length,
    averageProfitPercent: opportunities.length
      ? Math.round((profitSum / opportunities.length) * 1000) / 1000
      : 0,
    bestProfitPercent: Math.round(best * 1000) / 1000,
    sportBreakdown: [...sportMap.entries()].map(([sport, v]) => ({
      sport,
      count: v.count,
      avgProfit: Math.round((v.profitSum / v.count) * 1000) / 1000,
    })),
    marketBreakdown: [...marketMap.entries()].map(([market, count]) => ({
      market,
      count,
    })),
  };
}

export function startScannerLoop(): void {
  if (!process.env["ODDSJAM_API_KEY"]) {
    logger.info("Scanner: ODDSJAM_API_KEY not set — opportunities disabled");
    return;
  }

  const intervalMs = 30_000;
  logger.info({ intervalMs }, "Scanner: background refresh started");

  setTimeout(() => void getOpportunities({ refresh: true }), 5_000);
  setInterval(() => void getOpportunities({ refresh: true }), intervalMs);
}
