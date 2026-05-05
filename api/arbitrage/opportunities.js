// Vercel serverless function: GET /api/arbitrage/opportunities
// Uses Optic Odds API (api.opticodds.com/api/v3) with X-Api-Key auth

const BASE_URL = "https://api.opticodds.com/api/v3";

const NC_SPORTSBOOKS = [
  "draftkings", "fanduel", "betmgm", "caesars",
  "bet365", "fanatics", "hard_rock", "betrivers", "betparx",
];

const MAJOR_SPORTS = ["basketball", "baseball", "football", "hockey", "soccer", "tennis", "mma"];

const SPORT_LEAGUES = {
  basketball: "nba",
  baseball:   "mlb",
  football:   "nfl",
  hockey:     "nhl",
};

const MAIN_MARKETS = [
  "moneyline", "point_spread", "total_points",
  "total_goals", "total_rounds", "moneyline_3-way",
];

async function ojFetch(apiKey, path, params) {
  const url = new URL(BASE_URL + path);
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (Array.isArray(v)) v.forEach(item => url.searchParams.append(k, item));
      else if (v !== undefined && v !== "") url.searchParams.set(k, v);
    }
  }
  const res = await fetch(url.toString(), { headers: { "X-Api-Key": apiKey } });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`Optic Odds ${res.status}: ${text.slice(0, 200)}`);
  }
  return res.json();
}

async function getOdds(apiKey, sport) {
  const fixtureParams = { sport, is_live: "false" };
  const league = SPORT_LEAGUES[sport];
  if (league) fixtureParams.league = league;

  const fixtureRes = await ojFetch(apiKey, "/fixtures/active", fixtureParams);
  const fixtures = (fixtureRes.data ?? []).filter(f => f.has_odds).slice(0, 15);
  if (fixtures.length === 0) return [];

  const FIXTURE_BATCH = 5;
  const BOOK_BATCH    = 5;
  const oddsByFixture = new Map();

  for (let fi = 0; fi < fixtures.length; fi += FIXTURE_BATCH) {
    const fixBatch    = fixtures.slice(fi, fi + FIXTURE_BATCH);
    const fixtureIds  = fixBatch.map(f => f.id);
    for (let bi = 0; bi < NC_SPORTSBOOKS.length; bi += BOOK_BATCH) {
      const bookBatch = NC_SPORTSBOOKS.slice(bi, bi + BOOK_BATCH);
      const batchRes  = await ojFetch(apiKey, "/fixtures/odds", {
        fixture_id:  fixtureIds,
        sportsbook:  bookBatch,
        market:      MAIN_MARKETS,
        odds_format: "american",
      });
      for (const f of batchRes.data ?? []) {
        if (!oddsByFixture.has(f.id)) oddsByFixture.set(f.id, []);
        oddsByFixture.get(f.id).push(...(f.odds ?? []));
      }
    }
  }

  return fixtures
    .filter(f => oddsByFixture.has(f.id))
    .map(f => {
      const homeTeam = f.home_team_display ?? f.home_competitors?.[0]?.name ?? "Home";
      const awayTeam = f.away_team_display ?? f.away_competitors?.[0]?.name ?? "Away";
      const bySportsbook = new Map();
      for (const entry of oddsByFixture.get(f.id)) {
        if (!bySportsbook.has(entry.sportsbook)) bySportsbook.set(entry.sportsbook, []);
        bySportsbook.get(entry.sportsbook).push(entry);
      }
      const bookmakers = [];
      for (const [bookName, odds] of bySportsbook) {
        const byMarketLine = new Map();
        for (const o of odds) {
          const lineKey = `${o.market_id}::${o.grouping_key}`;
          if (!byMarketLine.has(lineKey)) byMarketLine.set(lineKey, []);
          byMarketLine.get(lineKey).push(o);
        }
        const markets = [];
        for (const [lineKey, entries] of byMarketLine) {
          const latestTs = Math.max(...entries.map(e => e.timestamp));
          markets.push({
            key: lineKey,
            last_update: new Date(latestTs * 1000).toISOString(),
            outcomes: entries.map(e => ({
              name:  e.name,
              price: e.price,
              ...(e.points != null ? { point: e.points } : {}),
            })),
          });
        }
        const bookKey = bookName.toLowerCase().replace(/\s+/g, "_").replace(/[^a-z0-9_]/g, "");
        bookmakers.push({ key: bookKey, title: bookName, markets });
      }
      return {
        id:           f.id,
        sport_key:    f.sport?.id ?? sport,
        home_team:    homeTeam,
        away_team:    awayTeam,
        commence_time: f.start_date,
        bookmakers,
      };
    });
}

function americanToDecimal(p) {
  return p >= 100 ? p / 100 + 1 : 100 / Math.abs(p) + 1;
}

function calcOptimalStakes(legs, bankroll) {
  const implied    = legs.map(l => 1 / l.decimalOdds);
  const totalImpl  = implied.reduce((a, b) => a + b, 0);
  return implied.map(imp => (bankroll * imp) / totalImpl);
}

function findArb(games) {
  const results = [];
  const now     = new Date().toISOString();

  for (const game of games) {
    const marketMap = new Map();

    for (const book of game.bookmakers) {
      for (const mkt of book.markets) {
        const hasPoints = mkt.outcomes.some(o => o.point !== undefined);
        const mktKey    = hasPoints
          ? `${mkt.key}_${mkt.outcomes[0]?.point ?? ""}`
          : mkt.key;

        if (!marketMap.has(mktKey)) marketMap.set(mktKey, new Map());
        const outcomeMap = marketMap.get(mktKey);

        for (const outcome of mkt.outcomes) {
          const outcomeName = outcome.point !== undefined
            ? `${outcome.name} ${outcome.point > 0 ? "+" : ""}${outcome.point}`
            : outcome.name;
          if (!outcomeMap.has(outcomeName)) outcomeMap.set(outcomeName, []);
          outcomeMap.get(outcomeName).push({
            bookmaker:      book.key,
            bookmakerTitle: book.title,
            price:          outcome.price,
            point:          outcome.point,
          });
        }
      }
    }

    for (const [mktKey, outcomeMap] of marketMap) {
      const outcomes = Array.from(outcomeMap.entries());
      if (outcomes.length < 2 || outcomes.length > 3) continue;

      const bestLegs = outcomes.map(([outcomeName, bets]) => {
        let best = bets[0];
        for (const b of bets) {
          const dB    = americanToDecimal(b.price);
          const dBest = americanToDecimal(best.price);
          if (dB > dBest) best = b;
        }
        return {
          outcome:        outcomeName,
          bookmaker:      best.bookmaker,
          bookmakerTitle: best.bookmakerTitle,
          price:          best.price,
          line:           best.point ?? null,
          decimalOdds:    americanToDecimal(best.price),
        };
      });

      const totalImplied = bestLegs.reduce((s, l) => s + 1 / l.decimalOdds, 0);
      if (totalImplied >= 1) continue;

      const profitPct = ((1 / totalImplied) - 1) * 100;
      const bankroll  = 1000;
      const stakes    = calcOptimalStakes(bestLegs, bankroll);
      const baseMkt   = mktKey.includes("::") ? mktKey.split("::")[0] : mktKey;

      results.push({
        event_id:      `${game.id}_${mktKey}`,
        sport_key:     game.sport_key,
        commence_time: game.commence_time,
        home_team:     game.home_team,
        away_team:     game.away_team,
        market:        baseMkt,
        margin_pct:    Math.round(profitPct * 100) / 100,
        legs: bestLegs.map((leg, i) => ({
          side:  leg.outcome,
          book:  leg.bookmakerTitle,
          price: leg.price,
          line:  leg.line,
          stake: Math.round((stakes[i] ?? 0) * 100) / 100,
        })),
      });
    }
  }

  return results.sort((a, b) => b.margin_pct - a.margin_pct);
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
    // Determine which sports to scan
    let sports = MAJOR_SPORTS;
    try {
      const sportsRes = await ojFetch(apiKey, "/sports/active", {});
      const active = (sportsRes.data ?? []).map(s => s.id);
      const major  = active.filter(s => MAJOR_SPORTS.includes(s));
      if (major.length > 0) sports = major;
    } catch (_) { /* fall back to hardcoded list */ }

    const query   = req.query || {};
    const sportFilter  = query.sport  ? [String(query.sport)]  : sports;
    const allGames = [];

    for (const sport of sportFilter) {
      try {
        const games = await getOdds(apiKey, sport);
        allGames.push(...games);
      } catch (_) { /* skip failed sports */ }
    }

    const opportunities = findArb(allGames);

    res.json({
      opportunities,
      total:      opportunities.length,
      fetched_at: new Date().toISOString(),
      configured: true,
    });
  } catch (e) {
    res.status(500).json({ error: "fetch_failed", message: e.message });
  }
};
