import { logger } from "./logger";
import { getOdds, getSports } from "./oddsjam";
import { findArbitrageOpportunities, type ArbitrageOpportunity } from "./arbitrage";

const MAJOR_SPORTS = ["baseball", "basketball", "football", "hockey", "soccer", "tennis", "mma"];
const MIN_PROFIT_PCT = 1.0;
const POLL_INTERVAL_MS = 60 * 1000;

// Track IDs already alerted so we don't spam the same opportunity
const seenIds = new Set<string>();

async function sendNtfyAlert(topic: string, opp: ArbitrageOpportunity): Promise<void> {
  const legs = opp.legs
    .map((l) => `${l.bookmakerTitle}: ${l.outcome} @ ${l.price > 0 ? "+" : ""}${l.price}`)
    .join("\n");

  const body = [
    `${opp.homeTeam} vs ${opp.awayTeam}`,
    `Sport: ${opp.sport}  |  Market: ${opp.market}`,
    legs,
    `Profit: ${opp.profitPercent.toFixed(2)}%`,
  ].join("\n");

  const res = await fetch(`https://ntfy.sh/${encodeURIComponent(topic)}`, {
    method: "POST",
    headers: {
      Title: `Arb Alert: ${opp.profitPercent.toFixed(2)}% profit`,
      Priority: "high",
      Tags: "money_with_wings,chart_with_upwards_trend",
      "Content-Type": "text/plain",
    },
    body,
  });

  if (!res.ok) {
    logger.warn({ status: res.status, topic }, "Monitor: ntfy.sh alert failed");
  } else {
    logger.info({ id: opp.id, profit: opp.profitPercent, topic }, "Monitor: alert sent");
  }
}

async function poll(): Promise<void> {
  const topic = process.env["NTFY_TOPIC"];
  if (!topic) return;

  let sports: string[];
  try {
    const all = await getSports();
    const major = all.filter((s) => s.active && MAJOR_SPORTS.includes(s.key));
    sports = major.length > 0 ? major.map((s) => s.key) : MAJOR_SPORTS;
  } catch {
    sports = MAJOR_SPORTS;
  }

  for (const sport of sports) {
    try {
      const games = await getOdds({ sport });
      const opps = findArbitrageOpportunities(games);

      for (const opp of opps) {
        if (opp.profitPercent >= MIN_PROFIT_PCT && !seenIds.has(opp.id)) {
          seenIds.add(opp.id);
          await sendNtfyAlert(topic, opp);
        }
      }
    } catch {
      // Skip sports that fail — don't block others
    }
  }

  // Prevent unbounded growth — keep only the most recent 500 IDs
  if (seenIds.size > 1000) {
    const arr = Array.from(seenIds);
    arr.slice(0, arr.length - 500).forEach((id) => seenIds.delete(id));
  }
}

export function startMonitor(): void {
  const topic = process.env["NTFY_TOPIC"];

  if (!topic) {
    logger.info("Monitor: NTFY_TOPIC not set — phone alerts disabled. Set it to enable.");
    return;
  }

  logger.info({ topic, intervalMs: POLL_INTERVAL_MS, minProfitPct: MIN_PROFIT_PCT }, "Monitor: started");

  // Wait 15 s after boot before first check so the server is fully ready
  setTimeout(() => {
    void poll();
    setInterval(() => void poll(), POLL_INTERVAL_MS);
  }, 15_000);
}

// Allow ad-hoc test from the /api/monitor/test endpoint
export async function sendTestAlert(): Promise<{ sent: boolean; topic: string | null }> {
  const topic = process.env["NTFY_TOPIC"] ?? null;
  if (!topic) return { sent: false, topic };

  await fetch(`https://ntfy.sh/${encodeURIComponent(topic)}`, {
    method: "POST",
    headers: {
      Title: "Arb Finder: test notification",
      Priority: "default",
      Tags: "white_check_mark",
      "Content-Type": "text/plain",
    },
    body: "Your phone alerts are working! You will be notified when an arbitrage opportunity above 1% is found.",
  });

  return { sent: true, topic };
}
