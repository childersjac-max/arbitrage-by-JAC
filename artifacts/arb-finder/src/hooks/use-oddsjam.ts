import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchGames, fetchOdds, fetchSports, OddsJamGame, OddsJamOdds, OddsJamSport } from '../lib/oddsjam-client';
import { apiUrl } from '../lib/api-base';


// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ArbLeg {
  bookmakerTitle: string;
  outcome: string;
  price: number;
  stake: number;
}

export interface ArbOpportunity {
  id: string;
  sport: string;
  market: string;
  homeTeam: string;
  awayTeam: string;
  commenceTime: string;
  detectedAt: string;
  profitPercent: number;
  totalImpliedProbability: number;
  legs: ArbLeg[];
}

export interface SportBreakdown {
  sport: string;
  count: number;
  avgProfit: number;
}

export interface MarketBreakdown {
  market: string;
  count: number;
}

export interface OpportunitiesSummary {
  totalOpportunities: number;
  averageProfitPercent: number;
  bestProfitPercent: number;
  sportBreakdown: SportBreakdown[];
  marketBreakdown: MarketBreakdown[];
}

// ---------------------------------------------------------------------------
// OddsJam data hooks
// ---------------------------------------------------------------------------

export function useGames(sport?: string) {
  return useQuery<OddsJamGame[], Error>({
    queryKey: ['games', sport ?? 'all'],
    queryFn: () => fetchGames(sport),
    staleTime: 30_000,
    refetchInterval: 30_000,
  });
}

export function useOdds(gameIds?: string[]) {
  return useQuery<OddsJamOdds[], Error>({
    queryKey: ['odds', gameIds ?? 'all'],
    queryFn: () => fetchOdds(gameIds),
    staleTime: 30_000,
    refetchInterval: 30_000,
    enabled: gameIds === undefined || gameIds.length > 0,
  });
}

export function useSports() {
  return useQuery<OddsJamSport[], Error>({
    queryKey: ['sports'],
    queryFn: fetchSports,
    staleTime: 5 * 60_000,
  });
}
/** OddsJam sports list aliased to the name used by alerts and sports pages. */
export function useOJSports() {
  return useSports();
}
// ---------------------------------------------------------------------------
// Arbitrage hooks
// ---------------------------------------------------------------------------

async function fetchArbitrageOpportunities(): Promise<ArbOpportunity[]> {
  const [games, odds] = await Promise.all([fetchGames(), fetchOdds()]);

  const opportunities: ArbOpportunity[] = [];

  for (const game of games) {
    const gameOdds = odds.filter(o => o.game_id === game.id);
    const markets = [...new Set(gameOdds.map(o => o.market_name))];

    for (const market of markets) {
      const marketOdds = gameOdds.filter(o => o.market_name === market);
      const outcomes = [...new Set(marketOdds.map(o => o.name))];

      const bestLegs: ArbLeg[] = outcomes.map(outcome => {
        const outcomOdds = marketOdds.filter(o => o.name === outcome);
        const best = outcomOdds.reduce((a, b) => {
          const aDecimal = a.price > 0 ? a.price / 100 + 1 : 100 / Math.abs(a.price) + 1;
          const bDecimal = b.price > 0 ? b.price / 100 + 1 : 100 / Math.abs(b.price) + 1;
          return bDecimal > aDecimal ? b : a;
        });
        const decimal = best.price > 0 ? best.price / 100 + 1 : 100 / Math.abs(best.price) + 1;
        return {
          bookmakerTitle: best.sportsbook,
          outcome,
          price: best.price,
          stake: 0,
          _decimal: decimal,
          _implied: 1 / decimal,
        } as any;
      });

      const totalImplied = bestLegs.reduce((sum, l) => sum + (l as any)._implied, 0);

      if (totalImplied < 1) {
        const profitPercent = (1 / totalImplied - 1) * 100;
        const bankroll = 1000;
        const legs: ArbLeg[] = bestLegs.map(l => ({
          bookmakerTitle: l.bookmakerTitle,
          outcome: l.outcome,
          price: l.price,
          stake: bankroll * (l as any)._implied / totalImplied,
        }));

        opportunities.push({
          id: `${game.id}-${market}`,
          sport: game.sport,
          market,
          homeTeam: game.home_team,
          awayTeam: game.away_team,
          commenceTime: game.start_date,
          detectedAt: new Date().toISOString(),
          profitPercent,
          totalImpliedProbability: totalImplied,
          legs,
        });
      }
    }
  }

  return opportunities.sort((a, b) => b.profitPercent - a.profitPercent);
}

/** Live arbitrage opportunities, refreshed every 30s. */
export function useArbitrageOpportunities() {
  return useQuery<ArbOpportunity[], Error>({
    queryKey: ['arbitrage-opportunities'],
    queryFn: fetchArbitrageOpportunities,
    staleTime: 30_000,
    refetchInterval: 30_000,
  });
}

/** Derived summary stats across all current arbitrage opportunities. */
export function useOpportunitiesSummary() {
  return useQuery<OpportunitiesSummary, Error>({
    queryKey: ['opportunities-summary'],
    queryFn: async () => {
      const opportunities = await fetchArbitrageOpportunities();

      const totalOpportunities = opportunities.length;
      const averageProfitPercent = totalOpportunities > 0
        ? opportunities.reduce((sum, o) => sum + o.profitPercent, 0) / totalOpportunities
        : 0;
      const bestProfitPercent = totalOpportunities > 0
        ? Math.max(...opportunities.map(o => o.profitPercent))
        : 0;

      const sportMap = new Map<string, { count: number; totalProfit: number }>();
      const marketMap = new Map<string, number>();

      for (const opp of opportunities) {
        const s = sportMap.get(opp.sport) ?? { count: 0, totalProfit: 0 };
        sportMap.set(opp.sport, { count: s.count + 1, totalProfit: s.totalProfit + opp.profitPercent });
        marketMap.set(opp.market, (marketMap.get(opp.market) ?? 0) + 1);
      }

      const sportBreakdown: SportBreakdown[] = [...sportMap.entries()]
        .map(([sport, { count, totalProfit }]) => ({ sport, count, avgProfit: totalProfit / count }))
        .sort((a, b) => b.count - a.count);

      const marketBreakdown: MarketBreakdown[] = [...marketMap.entries()]
        .map(([market, count]) => ({ market, count }))
        .sort((a, b) => b.count - a.count);

      return { totalOpportunities, averageProfitPercent, bestProfitPercent, sportBreakdown, marketBreakdown };
    },
    staleTime: 30_000,
    refetchInterval: 30_000,
  });
}

// ---------------------------------------------------------------------------
// Alerts hooks
// ---------------------------------------------------------------------------

export interface Alert {
  id: number;
  sport: string;
  min_profit: number;
  label: string;
  created_at: string;
}

interface CreateAlertPayload {
  sport: string;
  min_profit: number;
  label: string;
}

async function fetchAlerts(): Promise<Alert[]> {
  const res = await fetch(apiUrl('/api/alerts'));
  if (!res.ok) throw new Error(`Failed to fetch alerts: ${res.status}`);
  return res.json();
}

async function createAlert(payload: CreateAlertPayload): Promise<Alert> {
  const res = await fetch(apiUrl('/api/alerts'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`Failed to create alert: ${res.status}`);
  return res.json();
}

async function deleteAlert(id: number): Promise<void> {
  const res = await fetch(apiUrl(`/api/alerts/${id}`), { method: 'DELETE' });
  if (!res.ok) throw new Error(`Failed to delete alert: ${res.status}`);
}

export function useAlerts() {
  return useQuery<Alert[], Error>({
    queryKey: ['alerts'],
    queryFn: fetchAlerts,
  });
}

export function useCreateAlert() {
  const qc = useQueryClient();
  return useMutation<Alert, Error, CreateAlertPayload>({
    mutationFn: createAlert,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['alerts'] }),
  });
}

export function useDeleteAlert() {
  const qc = useQueryClient();
  return useMutation<void, Error, number>({
    mutationFn: deleteAlert,
    onMutate: async (id) => {
      await qc.cancelQueries({ queryKey: ['alerts'] });
      const prev = qc.getQueryData<Alert[]>(['alerts']);
      qc.setQueryData<Alert[]>(['alerts'], (old) => old?.filter((a) => a.id !== id) ?? []);
      return { prev };
    },
    onError: (_err, _id, context: any) => {
      if (context?.prev) qc.setQueryData(['alerts'], context.prev);
    },
    onSettled: () => qc.invalidateQueries({ queryKey: ['alerts'] }),
  });
}
