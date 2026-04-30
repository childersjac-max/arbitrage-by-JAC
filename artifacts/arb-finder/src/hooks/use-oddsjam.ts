import { useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchSports, fetchOdds } from "@/lib/oddsjam-client";
import { findArbitrageOpportunities, computeSummary } from "@/lib/arbitrage";

const MAJOR_SPORTS = [
  "americanfootball_nfl",
  "basketball_nba",
  "baseball_mlb",
  "icehockey_nhl",
  "soccer_epl",
  "soccer_spain_la_liga",
];

export function useOJSports() {
  return useQuery({
    queryKey: ["oj-sports"],
    queryFn: fetchSports,
    staleTime: 1000 * 60 * 10,
  });
}

export function useOJOdds(params: { sport: string; markets?: string; bookmakers?: string }, enabled = true) {
  return useQuery({
    queryKey: ["oj-odds", params.sport, params.markets, params.bookmakers],
    queryFn: () => fetchOdds(params),
    enabled: enabled && !!params.sport,
    staleTime: 1000 * 30,
  });
}

export function useArbitrageOpportunities(params?: {
  sport?: string;
  minProfit?: number;
  market?: string;
}) {
  return useQuery({
    queryKey: ["arb-opps", params?.sport, params?.minProfit, params?.market],
    queryFn: async () => {
      const sports = params?.sport ? [params.sport] : MAJOR_SPORTS;
      const allOpps = [];
      for (const sport of sports) {
        try {
          const games = await fetchOdds({ sport });
          const opps = findArbitrageOpportunities(games, params?.market);
          allOpps.push(...opps);
        } catch {
          // skip failed sports
        }
      }
      const minProfit = params?.minProfit ?? 0;
      return allOpps
        .filter((o) => o.profitPercent >= minProfit)
        .sort((a, b) => b.profitPercent - a.profitPercent);
    },
    refetchInterval: 30000,
    staleTime: 1000 * 25,
  });
}

export function useOpportunitiesSummary() {
  return useQuery({
    queryKey: ["arb-summary"],
    queryFn: async () => {
      const sports = MAJOR_SPORTS;
      const allOpps = [];
      for (const sport of sports) {
        try {
          const games = await fetchOdds({ sport });
          allOpps.push(...findArbitrageOpportunities(games));
        } catch {
          // skip
        }
      }
      return computeSummary(allOpps);
    },
    refetchInterval: 30000,
    staleTime: 1000 * 25,
  });
}
