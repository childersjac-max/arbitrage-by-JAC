const ODDSJAM_BASE = process.env.ODDSJAM_API_BASE || "https://api-dev.oddsjam.com/api/v2";

const MARKET_MAP = {
  Moneyline: "h2h", moneyline: "h2h",
  Spread: "spreads", spread: "spreads",
  Total: "totals", total: "totals",
};


// Only show opportunities involving these sportsbooks
const SELECTED_BOOKS = ['draftkings','fanduel','betmgm','caesars','bet365','fanatics','thescore'];
function normBook(b) { return String(b).toLowerCase().replace(/\s+/g,'').replace(/[^a-z0-9]/g,''); }
const NORM_BOOKS = SELECTED_BOOKS.map(normBook);

// Keep: moneyline, spreads, alt spreads, player props — exclude totals
function keepMarket(mkt) {
  var m = String(mkt || '').toLowerCase();
  return m.includes('moneyline') || m.includes('h2h') ||
         m.includes('spread') || m.includes('total') || m.includes('player');
}
function toAmerican(price) {
  if (typeof price === "number") return Math.round(price);
  const n = parseFloat(String(price));
  return isNaN(n) ? 0 : Math.round(n);
}

function toFloat(v) {
  if (v === null || v === undefined || v === "") return null;
  const n = parseFloat(String(v));
  return isNaN(n) ? null : n;
}

function calcStakes(legs, bankroll) {
  if (legs.length !== 2) return legs;
  var toImplied = function(p) { return p > 0 ? 100 / (p + 100) : -p / (-p + 100); };
  var imp1 = toImplied(legs[0].price);
  var imp2 = toImplied(legs[1].price);
  var total = imp1 + imp2;
  if (total <= 0) return legs;
  return [
    Object.assign({}, legs[0], { stake: Math.round((imp1 / total) * bankroll * 100) / 100 }),
    Object.assign({}, legs[1], { stake: Math.round((imp2 / total) * bankroll * 100) / 100 }),
  ];
}

module.exports = async function handler(req, res) {
  const apiKey = process.env.ODDSJAM_API_KEY;
  if (!apiKey) {
    return res.json({
      opportunities: [], total: 0,
      fetched_at: new Date().toISOString(),
      configured: false,
    });
  }

  try {
    const timestamp = Math.floor(Date.now() / 1000).toString();
    const params = new URLSearchParams({ key: apiKey });
    const query = req.query || {};
    if (query.sport) params.set("sport", String(query.sport));
    if (query.market) params.set("market", String(query.market));

    const body = {};
    if (query.sport) body.sport = String(query.sport);
    if (query.market) body.market = String(query.market);

    const response = await fetch(ODDSJAM_BASE + "/arbitrage?" + params.toString(), {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        Timestamp: timestamp,
      },
      body: JSON.stringify(body),
    });

    if (response.status === 403 || response.status === 401) {
      var errBody = {};
      try { errBody = await response.json(); } catch (e) {}
      var detail = String(errBody.detail || "");
      return res.json({
        opportunities: [], total: 0,
        fetched_at: new Date().toISOString(),
        configured: true,
        access_denied: true,
        access_denied_reason: detail || "Your OddsJam plan does not include arbitrage API access.",
      });
    }

    if (!response.ok) throw new Error("OddsJam API HTTP " + response.status);

    const data = await response.json();
    const rows = Array.isArray(data) ? data : ((data && data.data) || []);
    const DEFAULT_BANKROLL = 10000;

    const opportunities = rows.map(function(row) {
      if (!row || typeof row !== "object") return null;
      var mktRaw = String(row.market || row.market_name || "");
      var mkt = MARKET_MAP[mktRaw] || mktRaw.toLowerCase().replace(/\s+/g, "_");
      var legsRaw = row.legs || row.bets || [];
      var legs = legsRaw.map(function(leg) {
        return {
          side: String(leg.name || leg.bet_name || leg.side || ""),
          book: String(leg.sportsbook || leg.book || ""),
          price: toAmerican(leg.price || leg.odds || leg.american_odds),
          line: toFloat(leg.point || leg.line || leg.handicap),
        };
      });

      var margin = typeof row.profit_margin === "number" ? row.profit_margin
        : typeof row.margin_pct === "number" ? row.margin_pct
        : typeof row.arbitrage_percentage === "number" ? row.arbitrage_percentage
        : parseFloat(String(row.profit_margin || row.margin_pct || "0"));
      if (isNaN(margin)) margin = 0;
      if (margin > 0 && margin < 1.0) margin *= 100;

      return {
        event_id: String(row.game_id || row.id || row.event_id || ""),
        sport_key: String(row.sport_key || row.sport || ""),
        commence_time: String(row.start_date || row.commence_time || ""),
        home_team: String(row.home_team || ""),
        away_team: String(row.away_team || ""),
        market: mkt,
        margin_pct: Math.round(margin * 100) / 100,
        legs: calcStakes(legs, DEFAULT_BANKROLL),
      };
    }).filter(function(o) {
      if (!o || o.margin_pct <= 0) return false;
      if (!keepMarket(o.market)) return false;
      if (o.legs.length < 2) return false;
      // All legs must have valid American odds (≥ 100 or ≤ -100)
      if (o.legs.some(function(l) { return l.price > -100 && l.price < 100; })) return false;
      // All legs must be from a selected sportsbook
      if (!o.legs.every(function(l) { return NORM_BOOKS.includes(normBook(l.book)); })) return false;
      // True arb requires bets at ≥2 distinct sportsbooks — same-book "arbs" are not executable
      var books = o.legs.map(function(l) { return normBook(l.book); });
      var uniqueBooks = books.filter(function(b, i) { return books.indexOf(b) === i; });
      return uniqueBooks.length >= 2;
    })
      .sort(function(a, b) { return b.margin_pct - a.margin_pct; });

    res.json({
      opportunities, total: opportunities.length,
      fetched_at: new Date().toISOString(),
      configured: true,
    });
  } catch (e) {
    res.status(500).json({ error: "fetch_failed", message: e.message });
  }
};
