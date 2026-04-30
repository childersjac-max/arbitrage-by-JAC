import { logger } from "./logger";

const ODDSJAM_BASE_URL = "https://api.oddsjam.com/api/v2";

function getApiKey(): string {
  const key = process.env["ODDSJAM_API_KEY"];
  if (!key) throw new Error("ODDSJAM_API_KEY environment variable is not set");
  return key;
}

async function fetchOddsJam<T>(path: string, params?: Record<string, string>): Promise<T> {
  const url = new URL(`${ODDSJAM_BASE_URL}${path}`);
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (v) url.searchParams.set(k, v);
    }
  }
  const apiKey = getApiKey();
  logger.debug({ url: url.toString() }, "Fetching OddsJam API");
  const res = await fetch(url.toString(), {
    headers: { "x-api-key": apiKey },
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    logger.error({ status: res.status, body: text }, "OddsJam API error");
    throw new OddsJamError(res.status, text);
  }
  return res.json() as Promise<T>;
}

export class OddsJamError extends Error {
  constructor(public status: number, public body: string) {
    super(`OddsJam API error ${status}: ${body}`);
  }
}

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

export async function getSports(): Promise<OJSport[]> {
  const data = await fetchOddsJam<OJSport[] | { data: OJSport[] }>("/sports");
  return Array.isArray(data) ? data : (data as { data: OJSport[] }).data ?? [];
}

export async function getOdds(params: {
  sport: string;
  markets?: string;
  bookmakers?: string;
}): Promise<OJGame[]> {
  const queryParams: Record<string, string> = { sport_key: params.sport };
  if (params.markets) queryParams["markets"] = params.markets;
  if (params.bookmakers) queryParams["bookmakers"] = params.bookmakers;

  const data = await fetchOddsJam<OJGame[] | { data: OJGame[] }>("/game-odds", queryParams);
  return Array.isArray(data) ? data : (data as { data: OJGame[] }).data ?? [];
}
