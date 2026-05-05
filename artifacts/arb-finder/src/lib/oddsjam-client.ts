const ODDSJAM_BASE = "https://api.oddsjam.com/api/v2";

let cachedApiKey: string | null = null;

async function getApiKey(): Promise<string> {
  if (cachedApiKey) return cachedApiKey;
  const res = await fetch("/api/config");
  if (!res.ok) throw new Error("Failed to load API configuration");
  const data = await res.json() as { oddsjamApiKey: string };
  cachedApiKey = data.oddsjamApiKey;
  return cachedApiKey;
}

async function ojFetch<T>(path: string, params?: Record<string, string>): Promise<T> {
  const apiKey = await getApiKey();
  const url = new URL(`${ODDSJAM_BASE}${path}`);
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== null && v !== "") url.searchParams.set(k, v);
    }
  }
  const res = await fetch(url.toString(), {
    headers: { "x-api-key": apiKey },
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`OddsJam API error ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
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

function unwrap<T>(data: T | { data: T }): T {
  if (data && typeof data === "object" && "data" in (data as object)) {
    return (data as { data: T }).data;
  }
  return data as T;
}

export async function fetchSports(): Promise<OJSport[]> {
  const data = await ojFetch<OJSport[] | { data: OJSport[] }>("/sports");
  return unwrap(data);
}

export async function fetchOdds(params: {
  sport: string;
  markets?: string;
  bookmakers?: string;
}): Promise<OJGame[]> {
  const queryParams: Record<string, string> = { sport_key: params.sport };
  if (params.markets) queryParams["markets"] = params.markets;
  if (params.bookmakers) queryParams["bookmakers"] = params.bookmakers;
  const data = await ojFetch<OJGame[] | { data: OJGame[] }>("/game-odds", queryParams);
  return unwrap(data);
}
