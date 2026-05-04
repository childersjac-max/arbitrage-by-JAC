import { Router, type IRouter } from "express";

const router: IRouter = Router();

const NBA_RAW =
  "https://raw.githubusercontent.com/childersjac-max/nba-betting-model/main";

async function fetchJSON(url: string): Promise<unknown> {
  const res = await fetch(url + `?t=${Date.now()}`, {
    cache: "no-store",
  } as RequestInit);
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${url}`);
  return res.json();
}

function isObject(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

function toNum(v: unknown): number | null {
  if (v === null || v === undefined || v === "") return null;
  const n = parseFloat(String(v));
  return isNaN(n) ? null : n;
}

/**
 * Compute max drawdown % from an array of bankroll values.
 * Returns value in 0-1 scale.
 */
function maxDrawdown(history: number[]): number {
  let peak = -Infinity;
  let maxDd = 0;
  for (const val of history) {
    if (val > peak) peak = val;
    const dd = peak > 0 ? (peak - val) / peak : 0;
    if (dd > maxDd) maxDd = dd;
  }
  return maxDd;
}

router.get("/nba-model/predictions", async (req, res): Promise<void> => {
  try {
    const raw = await fetchJSON(`${NBA_RAW}/predictions.json`);
    const d = isObject(raw) ? raw : {};

    // Prefer all_recs (all recommendations for upcoming games);
    // fall back to pending_bets if present
    const recList: unknown[] = Array.isArray(d["all_recs"])
      ? (d["all_recs"] as unknown[])
      : Array.isArray(d["pending_bets"])
      ? (d["pending_bets"] as unknown[])
      : Array.isArray(raw)
      ? (raw as unknown[])
      : [];

    const predictions = recList
      .filter((r) => isObject(r))
      .map((r) => {
        const rec = r as Record<string, unknown>;
        return {
          game_id: rec["id"] ?? rec["event_id"] ?? "",
          matchup: rec["matchup"] ?? "",
          team: rec["team"] ?? "",
          market: rec["type"] ?? rec["market"] ?? "ML",
          side: rec["side"] ?? "",
          label: rec["label"] ?? "",
          reason: rec["reason"] ?? "",
          odds: toNum(rec["odds"]),
          model_prob: toNum(rec["model_prob"]),
          novig_prob: toNum(rec["novig_prob"]),
          edge: toNum(rec["edge"]),
          kelly_pct: toNum(rec["kelly_pct"]),
          grade: rec["grade"] ?? "",
          game_time: rec["date"] ?? "",
          best_book: rec["best_book"] ?? "",
          disagreement: toNum(rec["disagreement"]),
        };
      });

    const modelStats = isObject(d["model_stats"]) ? d["model_stats"] : {};

    res.json({
      predictions,
      total: predictions.length,
      generated_at: d["generated_at"] ?? null,
      fetched_at: new Date().toISOString(),
      model_version: d["model_version"] ?? null,
      model_stats: modelStats,
    });
  } catch (e: unknown) {
    req.log.error({ err: e }, "Failed to fetch NBA predictions");
    res.status(500).json({
      error: "fetch_failed",
      message: e instanceof Error ? e.message : String(e),
    });
  }
});

router.get("/nba-model/bet-log", async (req, res): Promise<void> => {
  try {
    const raw = await fetchJSON(`${NBA_RAW}/bet_log.json`);
    let bets: unknown[];
    if (Array.isArray(raw)) {
      bets = raw;
    } else if (isObject(raw) && Array.isArray(raw["bets"])) {
      bets = raw["bets"] as unknown[];
    } else {
      bets = [];
    }
    res.json({
      bets,
      total: bets.length,
      fetched_at: new Date().toISOString(),
    });
  } catch (e: unknown) {
    req.log.error({ err: e }, "Failed to fetch NBA bet log");
    res.status(500).json({
      error: "fetch_failed",
      message: e instanceof Error ? e.message : String(e),
    });
  }
});

router.get("/nba-model/backtest", async (req, res): Promise<void> => {
  try {
    const raw = await fetchJSON(`${NBA_RAW}/backtest.json`);
    const d = isObject(raw) ? raw : {};
    const fb = isObject(d["flat_bet"]) ? d["flat_bet"] : {};

    // bankroll_history is an array of floats — convert to {index, value} for recharts
    const bhRaw = Array.isArray(fb["bankroll_history"])
      ? (fb["bankroll_history"] as number[])
      : [];
    const bankroll_history = bhRaw.map((val, idx) => ({
      game: idx + 1,
      value: typeof val === "number" ? Math.round(val * 100) / 100 : 0,
    }));

    const maxDd = maxDrawdown(bhRaw);

    // roi_pct from flat_bet is already in percentage form (e.g. 225.41 = 225.41%)
    // Divide by 100 so formatPercent (which multiplies by 100) renders correctly.
    const roiRaw = toNum(fb["roi_pct"]);
    const roi_pct = roiRaw != null ? roiRaw / 100 : null;

    const total_pnl =
      toNum(fb["ending_bankroll"]) != null && toNum(fb["starting_bankroll"]) != null
        ? (toNum(fb["ending_bankroll"]) as number) -
          (toNum(fb["starting_bankroll"]) as number)
        : null;

    res.json({
      // Primary backtest metrics (from flat_bet)
      roi_pct,
      win_rate: toNum(fb["win_rate"]),
      total_bets: typeof fb["bets_placed"] === "number" ? fb["bets_placed"] : null,
      bets_won: typeof fb["bets_won"] === "number" ? fb["bets_won"] : null,
      total_pnl,
      threshold: toNum(fb["threshold"]),
      starting_bankroll: toNum(fb["starting_bankroll"]),
      ending_bankroll: toNum(fb["ending_bankroll"]),
      // Model quality (from top-level)
      sharpe: null, // not provided in the file
      max_drawdown_pct: maxDd,
      accuracy: toNum(d["accuracy"]),
      auc: toNum(d["auc"]),
      brier: toNum(d["brier"]),
      // Chart data
      bankroll_history,
      // Metadata
      monthly: isObject(d["monthly"]) ? d["monthly"] : null,
      feature_importance: Array.isArray(d["feature_importance"]) ? d["feature_importance"] : [],
      fetched_at: new Date().toISOString(),
    });
  } catch (e: unknown) {
    req.log.error({ err: e }, "Failed to fetch NBA backtest");
    res.status(500).json({
      error: "fetch_failed",
      message: e instanceof Error ? e.message : String(e),
    });
  }
});

export default router;
