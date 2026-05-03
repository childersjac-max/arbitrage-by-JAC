/**
 * src/lib/oddsjam-client.ts
 *
 * Browser-side OddsJam API client.
 *
 * Flow:
 *  1. On first call, fetches the OddsJam API key from /api/config (our own backend).
 *     This keeps the key out of the browser bundle — it is never in client-side code.
 *  2. Subsequent calls reuse the cached key (module-level singleton).
 *  3. All OddsJam requests are made directly from the browser using the fetched key.
 *
 * Vercel note: /api/config is a serverless function (api/config.ts in the repo root).
 * Dev note:    vite.config.ts proxies /api/* to localhost:3001 automatically.
 */

import { apiUrl } from './api-base';

const ODDSJAM_BASE = 'https://api.oddsjam.com/api/v2';

// Module-level cache — resolved once per page load
let apiKeyPromise: Promise<string> | null = null;

async function getApiKey(): Promise<string> {
  if (!apiKeyPromise) {
    apiKeyPromise = fetch(apiUrl('/api/config'))
      .then((res) => {
        if (!res.ok) throw new Error(`/api/config returned ${res.status}`);
        return res.json();
      })
      .then((data: { apiKey: string }) => {
        if (!data.apiKey) throw new Error('ODDSJAM_API_KEY is not configured on the server.');
        return data.apiKey;
      })
      .catch((err) => {
        // Reset so the next call retries instead of caching the failure
        apiKeyPromise = null;
        throw err;
      });
  }
  return apiKeyPromise;
}

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface OddsJamGame {
  id: string;
  sport: string;
  league: string;
  home_team: string;
  away_team: string;
  start_date: string;
}

export interface OddsJamOdds {
  game_id: string;
  sportsbook: string;
  market_name: string;
  name: string; // outcome label, e.g. team name or Over/Under
  price: number; // American odds integer
  is_main: boolean;
}

export interface OddsJamSport {
  name: string;
  season_type: string;
  is_live: boolean;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

async function ojFetch<T>(endpoint: string, params: Record<string, string> = {}): Promise<T> {
  const key = await getApiKey();
  const url = new URL(`${ODDSJAM_BASE}${endpoint}`);
  url.searchParams.set('key', key);
  Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v));

  const res = await fetch(url.toString());
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`OddsJam ${endpoint} → ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Public API methods
// ---------------------------------------------------------------------------

/** Fetch all active games, optionally filtered by sport. */
export async function fetchGames(sport?: string): Promise<OddsJamGame[]> {
  const params: Record<string, string> = {};
  if (sport) params['sport'] = sport;
  const data = await ojFetch<{ data: OddsJamGame[] }>('/games', params);
  return data.data ?? [];
}

/** Fetch live odds for a list of game IDs (or all games if omitted). */
export async function fetchOdds(gameIds?: string[]): Promise<OddsJamOdds[]> {
  const params: Record<string, string> = {};
  if (gameIds?.length) params['game_id'] = gameIds.join(',');
  const data = await ojFetch<{ data: OddsJamOdds[] }>('/game-odds', params);
  return data.data ?? [];
}

/** Fetch all sports supported by OddsJam. */
export async function fetchSports(): Promise<OddsJamSport[]> {
  const data = await ojFetch<{ data: OddsJamSport[] }>('/sports');
  return data.data ?? [];
}
