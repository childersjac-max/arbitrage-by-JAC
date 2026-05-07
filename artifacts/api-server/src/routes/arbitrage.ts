import { Router, type IRouter } from "express";

const router: IRouter = Router();

const ODDSJAM_BASE = process.env["ODDSJAM_API_BASE"] || "https://api-dev.oddsjam.com/api/v2";

interface ArbLeg {
  side: string;
  book: string;
  price: number;
  line: number | null;
  stake?: number;
}

interface ArbOpportunity {
  event_id: string;
  sport_key: string;
  commence_time: string;
  home_team: string;
  away_team: string;
  market: string;
  margin_pct: number;
  legs: ArbLeg[];
}

const MARKET_KEY_FROM_ODDSJAM: Record<string, string> = {
  "Moneyline": "h2h",
  "Spread": "spreads",
  "Total": "totals",
  "moneyline": "h2h",
  "spread": "spreads",
  "total": "totals",
};

function toAmerican(price: unknown): number {
  if (typeof price === "number") return Math.round(price);
  const n = parseFloat(String(price));
  return isNaN(n) ? 0 : Math.round(n);
}

function toFloat(v: unknown): number | null {
  if (v === null || v === undefined || v === "") return null;
  const n = parseFloat(String(v));
  return isNaN(n) ? null : n;
}

function calcStakes(legs: ArbLeg[], bankroll: number): ArbLeg[] {
  if (legs.length !== 2) return legs;
  const toImplied = (p: number) =>
    p > 0 ? 100 / (p + 100) : -p / (-p + 100);
  const imp1 = toImplied(legs[0].price);
  const imp2 = toImplied(legs[1].price);
  const total = imp1 + imp2;
  if (total <= 0) return legs;
  return [
    { ...legs[0], stake: Math.round((imp1 / total) * bankroll * 100) / 100 },
    { ...legs[1], stake: Math.round((imp2 / total) * bankroll * 100) / 100 },
  ];
}

router.get("/arbitrage/opportunities", async (req, res): Promise<void> => {
  const apiKey = process.env["ODDSJAM_API_KEY"];
  if (!apiKey) {
    res.json({
      opportunities: [],
      total: 0,
      fetched_at: new Date().toISOString(),
      configured: false,
    });
    return;
  }

  try {
    const timestamp = Math.floor(Date.now() / 1000).toString();
    const params = new URLSearchParams({ key: apiKey });
    if (req.query["sport"]) params.set("sport", String(req.query["sport"]));
    if (req.query["market"]) params.set("market", String(req.query["market"]));

    const body: Record<string, string> = {};
    if (req.query["sport"]) body["sport"] = String(req.query["sport"]);
    if (req.query["market"]) body["market"] = String(req.query["market"]);

    const response = await fetch(
      `${ODDSJAM_BASE}/arbitrage?${params.toString()}`,
      {
        method: "POST",
        headers: {
          "Accept": "application/json",
          "Content-Type": "application/json",
          "Timestamp": timestamp,
        },
        body: JSON.stringify(body),
      } as RequestInit,
    );

    if (response.status === 403 || response.status === 401) {
      const errBody = await response.json().catch(() => ({})) as Record<string, unknown>;
      const detail = String(errBody["detail"] || "");
      req.log.warn({ status: response.status, detail }, "OddsJam API access denied for arbitrage endpoint");
      res.json({
        opportunities: [],
        total: 0,
        fetched_at: new Date().toISOString(),
        configured: true,
        access_denied: true,
        access_denied_reason: detail || "Your OddsJam plan does not include arbitrage API access. Upgrade at oddsjam.com to unlock this feature.",
      });
      return;
    }

    if (!response.ok) {
      throw new Error(`OddsJam API HTTP ${response.status}`);
    }

    const data = await response.json() as { data?: unknown[] } | unknown[];
    const rows: unknown[] = Array.isArray(data) ? data : (data as { data?: unknown[] }).data || [];

    const DEFAULT_BANKROLL = 10000;
    const opportunities: ArbOpportunity[] = rows
      .map((row): ArbOpportunity | null => {
        if (!row || typeof row !== "object") return null;
        const r = row as Record<string, unknown>;
        const mktRaw = String(r["market"] || r["market_name"] || "");
        const mkt = MARKET_KEY_FROM_ODDSJAM[mktRaw] || mktRaw.toLowerCase().replace(/\s+/g, "_");
        const legsRaw = (r["legs"] || r["bets"] || []) as Record<string, unknown>[];
        const legs: ArbLeg[] = legsRaw.map((leg) => ({
          side: String(leg["name"] || leg["bet_name"] || leg["side"] || ""),
          book: String(leg["sportsbook"] || leg["book"] || ""),
          price: toAmerican(leg["price"] || leg["odds"] || leg["american_odds"]),
          line: toFloat(leg["point"] || leg["line"] || leg["handicap"]),
        }));

        let margin =
          typeof r["profit_margin"] === "number" ? r["profit_margin"]
          : typeof r["margin_pct"] === "number" ? r["margin_pct"]
          : typeof r["arbitrage_percentage"] === "number" ? r["arbitrage_percentage"]
          : parseFloat(String(r["profit_margin"] || r["margin_pct"] || "0"));
        if (isNaN(margin)) margin = 0;
        if (margin > 0 && margin < 1.0) margin *= 100;

        return {
          event_id: String(r["game_id"] || r["id"] || r["event_id"] || ""),
          sport_key: String(r["sport_key"] || r["sport"] || ""),
          commence_time: String(r["start_date"] || r["commence_time"] || ""),
          home_team: String(r["home_team"] || ""),
          away_team: String(r["away_team"] || ""),
          market: mkt,
          margin_pct: Math.round(margin * 100) / 100,
          legs: calcStakes(legs, DEFAULT_BANKROLL),
        };
      })
      .filter((o): o is ArbOpportunity => o !== null && o.margin_pct > 0)
      .sort((a, b) => b.margin_pct - a.margin_pct);

    res.json({
      opportunities,
      total: opportunities.length,
      fetched_at: new Date().toISOString(),
      configured: true,
    });
  } catch (e: unknown) {
    req.log.error({ err: e }, "Failed to fetch arbitrage opportunities");
    res.status(500).json({
      error: "fetch_failed",
      message: e instanceof Error ? e.message : String(e),
    });
  }
});

export default router;
