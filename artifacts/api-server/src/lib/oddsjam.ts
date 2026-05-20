import { logger } from "./logger";

const BASE_URL = "https://api.opticodds.com/api/v3";

const NC_SPORTSBOOKS = [
  "draftkings",  // DraftKings
  "fanduel",     // FanDuel
  "betmgm",      // BetMGM
  "caesars",     // Caesars
  "bet365",      // Bet365
  "fanatics",    // Fanatics
  "thescore",    // theScore Bet
];

function getApiKey(): string {
  const key = process.env["ODDSJAM_API_KEY"];
  if (!key) throw new Error("ODDSJAM_API_KEY environment variable is not set");
  return key;
}

async function ojFetch<T>(path: string, params?: Record<string, string | string[]>): Promise<T> {
  const url = new URL(`${BASE_URL}${path}`);
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (Array.isArray(v)) {
        for (const item of v) url.searchParams.append(k, item);
      } else if (v !== undefined && v !== "") {
        url.searchParams.set(k, v);
      }
    }
  }
  const apiKey = getApiKey();
  logger.debug({ url: url.toString() }, "Fetching Optic Odds API");
  const res = await fetch(url.toString(), {
    headers: { "X-Api-Key": apiKey },
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    logger.error({ status: res.status, body: text }, "Optic Odds API error");
    throw new OddsJamError(res.status, text);
  }
  return res.json() as Promise<T>;
}

export class OddsJamError extends Error {
  constructor(public status: number, public body: string) {
    super(`Optic Odds API error ${status}: ${body}`);
  }
}

// ── Response types from Optic Odds ──────────────────────────────────────────

interface OJSportRaw {
  id: string;
  name: string;
  numerical_id: number;
}

interface OJCompetitor {
  id: string;
  name: string;
  abbreviation: string;
}

interface OJFixtureRaw {
  id: string;
  sport: OJSportRaw;
  league?: { id: string; name: string };
  home_competitors: OJCompetitor[];
  away_competitors: OJCompetitor[];
  start_date: string;
  status: string;
  is_live: boolean;
  has_odds: boolean;
  home_team_display?: string;
  away_team_display?: string;
}

interface OJOddsEntry {
  sportsbook: string;
  market_id: string;
  market: string;
  name: string;
  price: number;
  points: number | null;
  grouping_key: string;
  timestamp: number;
}

interface OJFixtureOddsRaw extends OJFixtureRaw {
  odds: OJOddsEntry[];
}

// ── Public types used by the rest of the codebase ───────────────────────────

export interface OJSport {
  key: string;
  group: string;
  title: string;
  description: string;
  active: boolean;
  has_outrights: boolean;
}

export interface OJOutcome {
  name: string;
  price: number;
  point?: number;
}

export interface OJMarket {
  key: string;
  last_update: string;
  outcomes: OJOutcome[];
}

export interface OJBookmaker {
  key: string;
  title: string;
  markets: OJMarket[];
}

export interface OJGame {
  id: string;
  sport_key: string;
  sport_title: string;
  home_team: string;
  away_team: string;
  commence_time: string;
  bookmakers: OJBookmaker[];
}

// ── API methods ──────────────────────────────────────────────────────────────

export async function getSports(): Promise<OJSport[]> {
  const res = await ojFetch<{ data: OJSportRaw[] }>("/sports/active");
  return (res.data ?? []).map((s) => ({
    key: s.id,
    group: s.name,
    title: s.name,
    description: "",
    active: true,
    has_outrights: false,
  }));
}

const DEFAULT_LEAGUE: Record<string, string> = {
  basketball: "nba",
  baseball: "mlb",
  football: "nfl",
  hockey: "nhl",
};

export async function getOdds(params: {
  sport: string;
  league?: string;
  markets?: string;
  bookmakers?: string;
}): Promise<OJGame[]> {
  // 1. Fetch active (non-live) fixtures for this sport
  const fixtureParams: Record<string, string> = {
    sport: params.sport,
    is_live: "false",
  };
  const league = params.league ?? DEFAULT_LEAGUE[params.sport];
  if (league) fixtureParams["league"] = league;

  const fixtureRes = await ojFetch<{ data: OJFixtureRaw[] }>("/fixtures/active", fixtureParams);
  const fixtures = (fixtureRes.data ?? []).filter((f) => f.has_odds).slice(0, 15);

  if (fixtures.length === 0) return [];

  const sportsbooks = params.bookmakers
    ? params.bookmakers.split(",")
    : NC_SPORTSBOOKS;

  const marketFilter = params.markets ? params.markets.split(",") : null;

  // Markets to scan: standard + alt spreads + player props + alt player props
  const MAIN_MARKETS = [
    // Game lines
    "moneyline",
    "point_spread",
    // Totals
    "total_points", "total_goals", "total_rounds",
    // Alt spreads
    "alternate_spread",
    "alternate_point_spread",
    // Alt totals
    "alternate_total", "alternate_total_points", "alternate_total_goals",
    // Player props — NBA
    "player_points", "player_assists", "player_rebounds", "player_threes",
    "player_blocks", "player_steals", "player_points_rebounds_assists",
    // Player props — NFL
    "player_pass_yards", "player_pass_touchdowns", "player_pass_completions",
    "player_rush_yards", "player_rush_touchdowns",
    "player_receiving_yards", "player_receptions", "player_receiving_touchdowns",
    // Player props — MLB
    "player_hits", "player_home_runs", "player_strikeouts", "player_runs_batted_in",
    // Player props — NHL
    "player_goals", "player_shots_on_goal",
    // Alt player props
    "alternate_player_points", "alternate_player_assists", "alternate_player_rebounds",
    "alternate_player_pass_yards", "alternate_player_rush_yards",
    "alternate_player_receiving_yards", "alternate_player_home_runs",
    "alternate_player_strikeouts",
  ];
  const markets = marketFilter ?? MAIN_MARKETS;

  // 2. Fetch odds in batches — API limits: max 5 fixture_ids AND max 5 sportsbooks per request.
  //    We batch both dimensions and merge all odds entries back per fixture.
  const FIXTURE_BATCH = 5;
  const BOOK_BATCH = 5;

  // Accumulate odds keyed by fixture id so we can merge across sportsbook batches
  const oddsByFixture = new Map<string, OJOddsEntry[]>();

  for (let fi = 0; fi < fixtures.length; fi += FIXTURE_BATCH) {
    const fixtureBatch = fixtures.slice(fi, fi + FIXTURE_BATCH);
    const fixtureIds = fixtureBatch.map((f) => f.id);

    for (let bi = 0; bi < sportsbooks.length; bi += BOOK_BATCH) {
      const bookBatch = sportsbooks.slice(bi, bi + BOOK_BATCH);
      const batchRes = await ojFetch<{ data: OJFixtureOddsRaw[] }>("/fixtures/odds", {
        fixture_id: fixtureIds,
        sportsbook: bookBatch,
        market: markets,
        odds_format: "american",
      });
      for (const f of batchRes.data ?? []) {
        if (!oddsByFixture.has(f.id)) oddsByFixture.set(f.id, []);
        oddsByFixture.get(f.id)!.push(...(f.odds ?? []));
      }
    }
  }

  // Reconstruct array in fixture order with merged odds
  const allOddsData: OJFixtureOddsRaw[] = fixtures
    .filter((f) => oddsByFixture.has(f.id))
    .map((f) => ({ ...f, odds: oddsByFixture.get(f.id)! } as OJFixtureOddsRaw));

  const oddsRes = { data: allOddsData };

  const fixtureMap = new Map(fixtures.map((f) => [f.id, f]));

  // 3. Transform flat odds into nested OJGame format
  return (oddsRes.data ?? []).map((f): OJGame => {
    const fixture = fixtureMap.get(f.id);
    const homeTeam = f.home_team_display ?? fixture?.home_competitors[0]?.name ?? "Home";
    const awayTeam = f.away_team_display ?? fixture?.away_competitors[0]?.name ?? "Away";

    // Group odds by sportsbook
    const bySportsbook = new Map<string, OJOddsEntry[]>();
    for (const entry of f.odds ?? []) {
      if (marketFilter && !marketFilter.some((m) => entry.market_id.includes(m))) continue;
      const key = entry.sportsbook;
      if (!bySportsbook.has(key)) bySportsbook.set(key, []);
      bySportsbook.get(key)!.push(entry);
    }

    const bookmakers: OJBookmaker[] = [];
    for (const [bookName, odds] of bySportsbook) {
      // Group by market_id + grouping_key to get individual market lines
      const byMarketLine = new Map<string, OJOddsEntry[]>();
      for (const o of odds) {
        const lineKey = `${o.market_id}::${o.grouping_key}`;
        if (!byMarketLine.has(lineKey)) byMarketLine.set(lineKey, []);
        byMarketLine.get(lineKey)!.push(o);
      }

      const markets: OJMarket[] = [];
      for (const [lineKey, entries] of byMarketLine) {
        const marketId = lineKey.split("::")[0]!;
        const latestTs = Math.max(...entries.map((e) => e.timestamp));
        markets.push({
          key: lineKey,
          last_update: new Date(latestTs * 1000).toISOString(),
          outcomes: entries.map((e) => ({
            name: e.name,
            price: e.price,
            ...(e.points != null ? { point: e.points } : {}),
          })),
        });
        void marketId;
      }

      // Use bookmaker key as lowercase sportsbook name slug
      const bookKey = bookName.toLowerCase().replace(/\s+/g, "_").replace(/[^a-z0-9_]/g, "");
      bookmakers.push({ key: bookKey, title: bookName, markets });
    }

    return {
      id: f.id,
      sport_key: fixture?.sport?.id ?? params.sport,
      sport_title: fixture?.league?.name ?? fixture?.sport?.name ?? params.sport,
      home_team: homeTeam,
      away_team: awayTeam,
      commence_time: fixture?.start_date ?? f.start_date,
      bookmakers,
    };
  });
}
