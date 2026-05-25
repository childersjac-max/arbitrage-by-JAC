function splitCSVRow(line) {
  const result = [];
  let cur = "";
  let inQuote = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (ch === '"') {
      if (inQuote && line[i + 1] === '"') { cur += '"'; i++; }
      else { inQuote = !inQuote; }
    } else if (ch === "," && !inQuote) {
      result.push(cur); cur = "";
    } else {
      cur += ch;
    }
  }
  result.push(cur);
  return result;
}

function parseCSV(text) {
  const lines = text.trim().split(/\r?\n/);
  if (lines.length < 2) return [];
  const headers = splitCSVRow(lines[0]);
  return lines.slice(1).map((line) => {
    const vals = splitCSVRow(line);
    const obj = {};
    headers.forEach((h, i) => { obj[h.trim()] = (vals[i] || "").trim(); });
    return obj;
  });
}

function castBet(row) {
  const numFields = [
    "model_prob","fair_prob","edge_pct","ev_pct","bet_pct","bet_usd",
    "american_odds","n_signals","hours_to_game","side_injury_score",
    "opp_injury_score","arb_margin_pct",
  ];
  const out = Object.assign({}, row);
  for (const f of numFields) {
    if (out[f] !== undefined && out[f] !== "") {
      const n = parseFloat(out[f]);
      if (!isNaN(n)) out[f] = n;
    }
  }
  return out;
}

// In-memory cache — survives within a single warm function instance
let _cache = null;
let _cacheTime = 0;
const CACHE_TTL_MS = 45_000; // 45 seconds

module.exports = async function handler(req, res) {
  // Tell Vercel CDN to cache at the edge for 30s, serve stale for up to 60s
  res.setHeader("Cache-Control", "s-maxage=30, stale-while-revalidate=60");

  // Serve in-process cache if still fresh
  if (_cache && Date.now() - _cacheTime < CACHE_TTL_MS) {
    return res.json(_cache);
  }

  try {
    const r = await fetch(
      "https://raw.githubusercontent.com/childersjac-max/Line-Tracker-Model/main/pipeline_output/bet_slate_latest.csv?t=" + Date.now()
    );
    if (!r.ok) throw new Error("HTTP " + r.status);
    const text = await r.text();
    const bets = parseCSV(text)
      .filter((row) => row.sport && row.sport.trim() !== "")
      .map(castBet);

    // Only update cache when we get real data — don't cache empty responses
    if (bets.length > 0) {
      _cache = { bets, total: bets.length, fetched_at: new Date().toISOString() };
      _cacheTime = Date.now();
    }

    // If bets is empty but we have a previous cached result, serve it instead
    if (bets.length === 0 && _cache) {
      return res.json(_cache);
    }

    res.json({ bets, total: bets.length, fetched_at: new Date().toISOString() });
  } catch (e) {
    // On error, serve last known good cache if available
    if (_cache) {
      return res.json(_cache);
    }
    res.status(500).json({ error: "fetch_failed", message: e.message });
  }
};
