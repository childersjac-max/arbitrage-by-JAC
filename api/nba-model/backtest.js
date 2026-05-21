function isObject(v) {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

function toNum(v) {
  if (v === null || v === undefined || v === "") return null;
  const n = parseFloat(String(v));
  return isNaN(n) ? null : n;
}

function maxDrawdown(history) {
  let peak = -Infinity;
  let maxDd = 0;
  for (const val of history) {
    if (val > peak) peak = val;
    const dd = peak > 0 ? (peak - val) / peak : 0;
    if (dd > maxDd) maxDd = dd;
  }
  return maxDd;
}

module.exports = async function handler(req, res) {
  try {
    const r = await fetch(
      "https://raw.githubusercontent.com/childersjac-max/nba-betting-model/main/backtest.json?t=" + Date.now()
    );
    if (!r.ok) throw new Error("HTTP " + r.status);
    const raw = await r.json();
    const d = isObject(raw) ? raw : {};
    const fb = isObject(d.flat_bet) ? d.flat_bet : {};

    const bhRaw = Array.isArray(fb.bankroll_history) ? fb.bankroll_history : [];
    const bankroll_history = bhRaw.map((val, idx) => ({
      game: idx + 1,
      value: typeof val === "number" ? Math.round(val * 100) / 100 : 0,
    }));

    const roiRaw = toNum(fb.roi_pct);
    const roi_pct = roiRaw != null ? roiRaw / 100 : null;
    const ending = toNum(fb.ending_bankroll);
    const starting = toNum(fb.starting_bankroll);
    const total_pnl = ending != null && starting != null ? ending - starting : null;

    res.json({
      roi_pct,
      win_rate: toNum(fb.win_rate),
      total_bets: typeof fb.bets_placed === "number" ? fb.bets_placed : null,
      bets_won: typeof fb.bets_won === "number" ? fb.bets_won : null,
      total_pnl,
      threshold: toNum(fb.threshold),
      starting_bankroll: starting,
      ending_bankroll: ending,
      sharpe: null,
      max_drawdown_pct: maxDrawdown(bhRaw),
      accuracy: toNum(d.accuracy),
      auc: toNum(d.auc),
      brier: toNum(d.brier),
      bankroll_history,
      monthly: isObject(d.monthly) ? d.monthly : null,
      feature_importance: Array.isArray(d.feature_importance) ? d.feature_importance : [],
      fetched_at: new Date().toISOString(),
    });
  } catch (e) {
    res.status(500).json({ error: "fetch_failed", message: e.message });
  }
};
