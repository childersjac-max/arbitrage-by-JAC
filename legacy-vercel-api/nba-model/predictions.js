function isObject(v) {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

function toNum(v) {
  if (v === null || v === undefined || v === "") return null;
  const n = parseFloat(String(v));
  return isNaN(n) ? null : n;
}

module.exports = async function handler(req, res) {
  try {
    const r = await fetch(
      "https://raw.githubusercontent.com/childersjac-max/nba-betting-model/main/predictions.json?t=" + Date.now()
    );
    if (!r.ok) throw new Error("HTTP " + r.status);
    const raw = await r.json();
    const d = isObject(raw) ? raw : {};

    const recList = Array.isArray(d.all_recs) ? d.all_recs
      : Array.isArray(d.pending_bets) ? d.pending_bets
      : Array.isArray(raw) ? raw : [];

    const predictions = recList.filter(isObject).map((rec) => ({
      game_id: rec.id != null ? rec.id : (rec.event_id != null ? rec.event_id : ""),
      matchup: rec.matchup != null ? rec.matchup : "",
      team: rec.team != null ? rec.team : "",
      market: rec.type != null ? rec.type : (rec.market != null ? rec.market : "ML"),
      side: rec.side != null ? rec.side : "",
      label: rec.label != null ? rec.label : "",
      reason: rec.reason != null ? rec.reason : "",
      odds: toNum(rec.odds),
      model_prob: toNum(rec.model_prob),
      novig_prob: toNum(rec.novig_prob),
      edge: toNum(rec.edge),
      kelly_pct: toNum(rec.kelly_pct),
      grade: rec.grade != null ? rec.grade : "",
      game_time: rec.date != null ? rec.date : "",
      best_book: rec.best_book != null ? rec.best_book : "",
      disagreement: toNum(rec.disagreement),
    }));

    res.json({
      predictions,
      total: predictions.length,
      generated_at: d.generated_at != null ? d.generated_at : null,
      fetched_at: new Date().toISOString(),
      model_version: d.model_version != null ? d.model_version : null,
      model_stats: isObject(d.model_stats) ? d.model_stats : {},
    });
  } catch (e) {
    res.status(500).json({ error: "fetch_failed", message: e.message });
  }
};
