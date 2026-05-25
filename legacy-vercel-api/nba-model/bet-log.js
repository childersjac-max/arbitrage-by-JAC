module.exports = async function handler(req, res) {
  try {
    const r = await fetch(
      "https://raw.githubusercontent.com/childersjac-max/nba-betting-model/main/bet_log.json?t=" + Date.now()
    );
    if (!r.ok) throw new Error("HTTP " + r.status);
    const raw = await r.json();
    let bets;
    if (Array.isArray(raw)) {
      bets = raw;
    } else if (raw && typeof raw === "object" && Array.isArray(raw.bets)) {
      bets = raw.bets;
    } else {
      bets = [];
    }
    res.json({ bets, total: bets.length, fetched_at: new Date().toISOString() });
  } catch (e) {
    res.status(500).json({ error: "fetch_failed", message: e.message });
  }
};
