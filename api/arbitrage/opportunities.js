// Vercel serverless function: GET /api/arbitrage/opportunities
// Uses Optic Odds API (api.opticodds.com/api/v3) with X-Api-Key auth

const BASE_URL = "https://api.opticodds.com/api/v3";

const NC_SPORTSBOOKS = [
  "draftkings", "fanduel", "betmgm", "caesars",
  "bet365", "fanatics", "hard_rock", "betrivers", "betparx",
];

// Sport ID → league filter for Optic Odds API.
// Entries with null league use the sport ID directly (no extra filter).
const SPORT_CONFIGS = [
  { sport: "basketball", league: "nba"  },
  { sport: "baseball",   league: "mlb"  },
  { sport: "football",   league: "nfl"  },
  // NHL — try multiple formats to handle whatever ID Optic Odds uses
  { sport: "hockey",     league: "nhl"  },
  { sport: "nhl",        league: null   },
  { sport: "ice_hockey", league: "nhl"  },
  { sport: "soccer",     league: null   },
  { sport: "tennis",     league: null   },
  { sport: "mma",        league: null   },
];

const MAIN_MARKETS = [
  "moneyline", "point_spread", "total_points",
  "total_goals", "total_rounds",
];

async function ojFetch(apiKey, path, params) {
  const url = new URL(BASE_URL + path);
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (Array.isArray(v)) v.forEach(item => url.searchParams.append(k, item));
      else if (v !== undefined && v !== null && v !== "") url.searchParams.set(k, v);
    }
  }
  const res = await fetch(url.toString(), { headers: { "X-Api-Key": apiKey } });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`Optic Odds ${res.status}: ${text.slice(0, 200)}`);
  }
  return res.json();
}

async function getFixturesForSport(apiKey, sport, league) {
  const params = { sport, is_live: "false" };
  if (league) params.league = league;
  try {
    const res = await ojFetch(apiKey, "/fixtures/active", params);
    return (res.data ?? []).filter(f => f.has_odds);
  } catch (_) {
    return [];
  }
}

async function getOddsForFixtures(apiKey, sport, fixtures) {
  if (fixtures.length === 0) return new Map();

  const FIXTURE_BATCH = 5;
  const BOOK_BATCH    = 5;
  const oddsByFixture = new Map();

  const capped = fixtures.slice(0, 20);

  for (let fi = 0; fi < capped.length; fi += FIXTURE_BATCH) {
    const fixBatch   = capped.slice(fi, fi + FIXTURE_BATCH);
    const fixtureIds = fixBatch.map(f => f.id);

    for (let bi = 0; bi < NC_SPORTSBOOKS.length; bi += BOOK_BATCH) {
      const bookBatch = NC_SPORTSBOOKS.slice(bi, bi + BOOK_BATCH);
      try {
        const batchRes = await ojFetch(apiKey, "/fixtures/odds", {
          fixture_id:  fixtureIds,
          sportsbook:  bookBatch,
          market:      MAIN_MARKETS,
          odds_format: "american",
        });
        for (const f of batchRes.data ?? []) {
          if (!oddsByFixture.has(f.id)) oddsByFixture.set(f.id, []);
          oddsByFixture.get(f.id).push(...(f.odds ?? []));
        }
      } catch (_) { /* skip failed batch */ }
    }
  }

  return oddsByFixture;
}

async function getGamesForSport(apiKey, sport, league) {
  const fixtures    = await getFixturesForSport(apiKey, sport, league);
  if (fixtures.length === 0) return [];

  const oddsByFixture = await getOddsForFixtures(apiKey, sport, fixtures);

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
        id:            f.id,
        sport_key:     f.sport?.id ?? sport,
        home_team:     homeTeam,
        away_team:     awayTeam,
        commence_time: f.start_date,
        bookmakers,
      };
    });
}

function americanToDecimal(p) {
  return p >= 100 ? p / 100 + 1 : 100 / Math.abs(p) + 1;
}

function calcOptimalStakes(legs, bankroll) {
  const implied   = legs.map(l => 1 / l.decimalOdds);
  const totalImpl = implied.reduce((a, b) => a + b, 0);
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
          const ptStr = outcome.point !== undefined
            ? `${outcome.point > 0 ? "+" : ""}${outcome.point}`
            : "";
        const name = (ptStr && !outcome.name.includes(ptStr))
            ? `${outcome.name} ${ptStr}`
            : outcome.name;
          if (!outcomeMap.has(name)) outcomeMap.set(name, []);
          outcomeMap.get(name).push({
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
      // Only 2-outcome markets guarantee a win on one side — skip 3-way (draw) and 1-way
      if (outcomes.length !== 2) continue;
      // Extra safety: skip if any outcome name suggests a draw or tie
      const hasDraw = outcomes.some(([name]) =>
        /draw|tie|void|push/i.test(name)
      );
      if (hasDraw) continue;

      const bestLegs = outcomes.map(([outcomeName, bets]) => {
        let best = bets[0];
        for (const b of bets) {
          if (americanToDecimal(b.price) > americanToDecimal(best.price)) best = b;
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
    const query       = req.query || {};
    const sportFilter = query.sport ? String(query.sport) : null;

    // Determine which sport configs to run
    let configs = SPORT_CONFIGS;
    if (sportFilter) {
      configs = SPORT_CONFIGS.filter(c => c.sport === sportFilter || c.league === sportFilter);
      if (configs.length === 0) configs = [{ sport: sportFilter, league: null }];
    }

    // Fetch all sports concurrently; deduplicate fixtures by game ID
    const seenFixtureIds = new Set();
    const allGames = [];

    const results = await Promise.allSettled(
      configs.map(({ sport, league }) => getGamesForSport(apiKey, sport, league))
    );

    for (const r of results) {
      if (r.status === "fulfilled") {
        for (const game of r.value) {
          if (!seenFixtureIds.has(game.id)) {
            seenFixtureIds.add(game.id);
            allGames.push(game);
          }
        }
      }
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
