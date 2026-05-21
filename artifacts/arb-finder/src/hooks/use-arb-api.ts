import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

const base = () => import.meta.env.BASE_URL.replace(/\/$/, "");

export interface ArbLeg {
  bookmaker: string;
  bookmakerTitle: string;
  outcome: string;
  price: number;
  stake: number;
  impliedProbability: number;
}

export interface ArbOpportunity {
  id: string;
  gameId: string;
  sport: string;
  league?: string;
  homeTeam: string;
  awayTeam: string;
  commenceTime: string;
  market: string;
  profitPercent: number;
  totalImpliedProbability: number;
  legs: ArbLeg[];
  detectedAt: string;
}

export interface OpportunitiesSummary {
  totalOpportunities: number;
  averageProfitPercent: number;
  bestProfitPercent: number;
  sportBreakdown: Array<{ sport: string; count: number; avgProfit: number }>;
  marketBreakdown: Array<{ market: string; count: number }>;
}

export interface HistoryBucket {
  time: string;
  hour?: number;
  label?: string;
  count: number;
  avgProfit: number;
  maxProfit: number;
}

export interface HistoryChartResponse {
  range: string;
  sport: string;
  league: string;
  since: string;
  until: string;
  bucketUnit: string;
  buckets: HistoryBucket[];
  summary: {
    totalOpportunities: number;
    avgProfit: number;
    bestProfit: number;
    avgDurationMinutes: number;
  };
  opportunities: Array<{
    id: number;
    oppId: string;
    sport: string;
    league: string | null;
    homeTeam: string;
    awayTeam: string;
    market: string;
    profitPercent: number;
    firstSeenAt: string;
    lastSeenAt: string;
    durationMinutes: number;
    legs: ArbLeg[];
  }>;
  sportFilters: Array<{ value: string; label: string }>;
  leagueFilters: Array<{ value: string; label: string }>;
}

export function useHealthCheck() {
  return useQuery({
    queryKey: ["healthz"],
    queryFn: () => apiGet<{ status: string }>("/api/healthz"),
    refetchInterval: 30_000,
  });
}

async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${base()}${path}`);
  if (!res.ok) throw new Error(`API ${path} failed: ${res.status}`);
  return res.json() as Promise<T>;
}

export function useArbitrageOpportunities() {
  return useQuery({
    queryKey: ["opportunities"],
    queryFn: () => apiGet<ArbOpportunity[]>("/api/opportunities"),
    refetchInterval: 30_000,
  });
}

export function useOpportunitiesSummary() {
  return useQuery({
    queryKey: ["opportunities-summary"],
    queryFn: () => apiGet<OpportunitiesSummary>("/api/opportunities/summary"),
    refetchInterval: 30_000,
  });
}

export function useHistoryChart(
  range: string,
  sport: string,
  league: string,
) {
  const params = new URLSearchParams({ range, sport, league });
  return useQuery({
    queryKey: ["history-chart", range, sport, league],
    queryFn: () =>
      apiGet<HistoryChartResponse>(`/api/history/chart?${params}`),
    refetchInterval: 60_000,
  });
}

export interface OJSport {
  key: string;
  group: string;
  title: string;
  description: string;
  active: boolean;
  hasOutrights: boolean;
}

export function useOJSports() {
  return useQuery({
    queryKey: ["sports"],
    queryFn: () => apiGet<OJSport[]>("/api/sports"),
    staleTime: 300_000,
  });
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

export interface FlatOddsRow {
  bookmaker: string;
  bookmakerTitle: string;
  outcome: string;
  price: number;
  point?: number;
}

export interface OddsGameView {
  id: string;
  sport: string;
  homeTeam: string;
  awayTeam: string;
  commenceTime: string;
  bookmakerOdds: FlatOddsRow[];
}

function flattenGames(games: OJGame[]): OddsGameView[] {
  return games.map((game) => {
    const bookmakerOdds: FlatOddsRow[] = [];
    for (const b of game.bookmakers) {
      for (const m of b.markets) {
        for (const o of m.outcomes) {
          bookmakerOdds.push({
            bookmaker: b.key,
            bookmakerTitle: b.title,
            outcome: o.name,
            price: o.price,
            point: o.point,
          });
        }
      }
    }
    return {
      id: game.id,
      sport: game.sport_key,
      homeTeam: game.home_team,
      awayTeam: game.away_team,
      commenceTime: game.commence_time,
      bookmakerOdds,
    };
  });
}

export function useOJOdds(sport: string, markets?: string) {
  const params = new URLSearchParams({ sport });
  if (markets) params.set("markets", markets);
  return useQuery({
    queryKey: ["odds", sport, markets],
    queryFn: async () => flattenGames(await apiGet<OJGame[]>(`/api/odds?${params}`)),
    enabled: !!sport,
    refetchInterval: 60_000,
  });
}

export interface AlertRule {
  id: string;
  minProfitPercent: number;
  sport?: string;
  market?: string;
  createdAt: string;
}

export function useAlerts() {
  return useQuery({
    queryKey: ["alerts"],
    queryFn: () => apiGet<AlertRule[]>("/api/alerts"),
  });
}

export function useCreateAlert() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      minProfitPercent: number;
      sport?: string;
      market?: string;
    }) =>
      fetch(`${base()}/api/alerts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }).then(async (r) => {
        if (!r.ok) throw new Error("Failed to create alert");
        return r.json() as Promise<AlertRule>;
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["alerts"] }),
  });
}

export function useDeleteAlert() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      fetch(`${base()}/api/alerts/${id}`, { method: "DELETE" }).then((r) => {
        if (!r.ok) throw new Error("Failed to delete alert");
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["alerts"] }),
  });
}
