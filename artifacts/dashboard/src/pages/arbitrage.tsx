import { useState } from "react";
import {
  useGetArbitrageOpportunities,
  getGetArbitrageOpportunitiesQueryKey,
} from "@workspace/api-client-react";
import { formatMoney, formatTimeAgo, formatOdds } from "@/lib/format";
import { Card, CardContent } from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { KeyRound, RefreshCw, Info, AlertCircle, TrendingUp, MapPin } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

// ── Market label helpers ─────────────────────────────────────────────────────

const MARKET_LABELS: Record<string, string> = {
  // ── Full Game ────────────────────────────────────────────
  moneyline:              "Full Game Moneyline",
  "moneyline_3-way":      "Full Game 3-Way Moneyline",
  point_spread:           "Full Game Point Spread",
  total_points:           "Full Game Total Points",
  total_goals:            "Full Game Total Goals",
  total_rounds:           "Full Game Total Rounds",
  h2h:                    "Full Game Moneyline",
  spreads:                "Full Game Spread",
  totals:                 "Full Game Total",
  draw_no_bet:            "Full Game Draw No Bet",
  btts:                   "Full Game Both Teams to Score",
  asian_handicap:         "Full Game Asian Handicap",
  alternate_spread:       "Full Game Alternate Spread",
  alternate_total:        "Full Game Alternate Total",
  // ── 1st Half ─────────────────────────────────────────────
  "1h_moneyline":         "1st Half Moneyline",
  "1h_spread":            "1st Half Point Spread",
  "1h_total":             "1st Half Total Points",
  "1h_total_goals":       "1st Half Total Goals",
  "1h_asian_handicap":    "1st Half Asian Handicap",
  // ── 2nd Half ─────────────────────────────────────────────
  "2h_moneyline":         "2nd Half Moneyline",
  "2h_spread":            "2nd Half Point Spread",
  "2h_total":             "2nd Half Total Points",
  "2h_total_goals":       "2nd Half Total Goals",
  // ── 1st Quarter ──────────────────────────────────────────
  "1q_moneyline":         "1st Quarter Moneyline",
  "1q_spread":            "1st Quarter Point Spread",
  "1q_total":             "1st Quarter Total Points",
  // ── 2nd Quarter ──────────────────────────────────────────
  "2q_moneyline":         "2nd Quarter Moneyline",
  "2q_spread":            "2nd Quarter Point Spread",
  "2q_total":             "2nd Quarter Total Points",
  // ── 3rd Quarter ──────────────────────────────────────────
  "3q_moneyline":         "3rd Quarter Moneyline",
  "3q_spread":            "3rd Quarter Point Spread",
  "3q_total":             "3rd Quarter Total Points",
  // ── 4th Quarter ──────────────────────────────────────────
  "4q_moneyline":         "4th Quarter Moneyline",
  "4q_spread":            "4th Quarter Point Spread",
  "4q_total":             "4th Quarter Total Points",
  // ── 1st Period (Hockey) ───────────────────────────────────
  "1p_moneyline":         "1st Period Moneyline",
  "1p_spread":            "1st Period Puck Line",
  "1p_total":             "1st Period Total Goals",
  // ── 2nd Period (Hockey) ───────────────────────────────────
  "2p_moneyline":         "2nd Period Moneyline",
  "2p_spread":            "2nd Period Puck Line",
  "2p_total":             "2nd Period Total Goals",
  // ── 3rd Period (Hockey) ───────────────────────────────────
  "3p_moneyline":         "3rd Period Moneyline",
  "3p_spread":            "3rd Period Puck Line",
  "3p_total":             "3rd Period Total Goals",
};

function getMarketLabel(market: string): string {
  if (MARKET_LABELS[market]) return MARKET_LABELS[market];
  return market
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function getMarketDetail(
  market: string,
  legs: Array<{ line?: number | null }>,
): string {
  const label = getMarketLabel(market);
  const line = legs[0]?.line;
  if (line != null && market.includes("spread"))
    return `${label}  (${line > 0 ? `+${line}` : line})`;
  if (line != null && market.includes("total"))
    return `${label}  (O/U ${Math.abs(line)})`;
  return label;
}

// ── Math helpers ─────────────────────────────────────────────────────────────

function toImplied(price: number): number {
  return price > 0 ? 100 / (price + 100) : -price / (-price + 100);
}

function americanToDecimal(price: number): number {
  return price >= 100 ? price / 100 + 1 : 100 / Math.abs(price) + 1;
}

function calcOptimalStakes(legs: Array<{ price: number }>, bankroll: number): number[] {
  const implied = legs.map((l) => toImplied(l.price));
  const total   = implied.reduce((a, b) => a + b, 0);
  if (total <= 0) return legs.map(() => bankroll / legs.length);
  return implied.map((imp) => Math.round((bankroll * imp) / total * 100) / 100);
}

function calcProfitIfWins(
  legs: Array<{ price: number }>,
  betSizes: number[],
  winnerIdx: number,
): number {
  const decimal    = americanToDecimal(legs[winnerIdx].price);
  const winnerBet  = betSizes[winnerIdx] ?? 0;
  const otherBets  = betSizes.reduce((s, b, i) => (i !== winnerIdx ? s + b : s), 0);
  return winnerBet * (decimal - 1) - otherBets;
}

// ── Styling helpers ──────────────────────────────────────────────────────────

function marginColor(pct: number): string {
  if (pct > 2) return "border-green-500 text-green-500 bg-green-500/10";
  if (pct > 1) return "border-yellow-500 text-yellow-500 bg-yellow-500/10";
  return "border-muted-foreground text-muted-foreground";
}

// Distinct accent colors per bet position so it's impossible to mix up
const BET_COLORS = [
  {
    badge:    "bg-blue-500/15 border-blue-500/50 text-blue-400",
    book:     "text-blue-400",
    input:    "bg-blue-500/10 border-blue-500/40 text-blue-200 focus:ring-blue-500",
    dot:      "bg-blue-500",
    strip:    "border-l-blue-500",
  },
  {
    badge:    "bg-orange-500/15 border-orange-500/50 text-orange-400",
    book:     "text-orange-400",
    input:    "bg-orange-500/10 border-orange-500/40 text-orange-200 focus:ring-orange-500",
    dot:      "bg-orange-500",
    strip:    "border-l-orange-500",
  },
  {
    badge:    "bg-purple-500/15 border-purple-500/50 text-purple-400",
    book:     "text-purple-400",
    input:    "bg-purple-500/10 border-purple-500/40 text-purple-200 focus:ring-purple-500",
    dot:      "bg-purple-500",
    strip:    "border-l-purple-500",
  },
];

function betColor(idx: number) {
  return BET_COLORS[idx % BET_COLORS.length];
}

// ── Component ────────────────────────────────────────────────────────────────

export default function Arbitrage() {
  const [bankroll, setBankroll]           = useState<number>(100);
  const [bankrollInput, setBankrollInput] = useState<string>("100");
  const [customBets, setCustomBets]       = useState<Record<string, string[]>>({});

  const { data, isLoading, error, refetch, isFetching } =
    useGetArbitrageOpportunities(undefined, {
      query: {
        queryKey: getGetArbitrageOpportunitiesQueryKey(),
        refetchInterval: 30000,
      },
    });

  const handleBankrollChange = (val: string) => {
    setBankrollInput(val);
    const n = parseFloat(val);
    if (!isNaN(n) && n > 0) {
      setBankroll(n);
      setCustomBets({});
    }
  };

  function getOptimalStrs(opp: { legs: Array<{ price: number }> }): string[] {
    return calcOptimalStakes(opp.legs, bankroll).map((s) => s.toFixed(2));
  }

  function getDisplayValues(opp: { event_id: string; legs: Array<{ price: number }> }): string[] {
    return customBets[opp.event_id] ?? getOptimalStrs(opp);
  }

  function getParsedBets(opp: { event_id: string; legs: Array<{ price: number }> }): number[] {
    const displays = getDisplayValues(opp);
    const optimal  = calcOptimalStakes(opp.legs, bankroll);
    return displays.map((v, i) => {
      const n = parseFloat(v);
      return isNaN(n) ? (optimal[i] ?? 0) : n;
    });
  }

  function handleBetInput(
    eventId: string,
    legIdx: number,
    val: string,
    opp: { legs: Array<{ price: number }> },
  ) {
    setCustomBets((prev) => {
      const current = prev[eventId] ?? getOptimalStrs(opp);
      const updated = [...current];
      updated[legIdx] = val;
      return { ...prev, [eventId]: updated };
    });
  }

  // ── Loading / error states ───────────────────────────────────────────────

  if (isLoading && !data) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-[300px] w-full" />
        <Skeleton className="h-[300px] w-full" />
      </div>
    );
  }

  if (data?.configured === false) {
    return (
      <div className="max-w-2xl mx-auto mt-12">
        <Alert className="border-primary bg-primary/5">
          <KeyRound className="h-5 w-5 text-primary" />
          <AlertTitle className="text-lg font-semibold text-primary">
            OddsJam API Key Required
          </AlertTitle>
          <AlertDescription className="mt-2 text-sm leading-relaxed text-muted-foreground">
            Set the{" "}
            <code className="bg-secondary px-1 py-0.5 rounded text-foreground">ODDSJAM_API_KEY</code>{" "}
            environment variable to enable live arbitrage scanning.
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  if (data?.access_denied) {
    return (
      <div className="max-w-2xl mx-auto mt-12">
        <Alert className="border-yellow-500 bg-yellow-500/5">
          <KeyRound className="h-5 w-5 text-yellow-500" />
          <AlertTitle className="text-lg font-semibold text-yellow-600 dark:text-yellow-400">
            Arbitrage Access Not Included
          </AlertTitle>
          <AlertDescription className="mt-2 text-sm leading-relaxed text-muted-foreground">
            {data.access_denied_reason || "Your plan does not include arbitrage API access."}{" "}
            Visit{" "}
            <a href="https://oddsjam.com" target="_blank" rel="noopener noreferrer"
              className="underline text-foreground hover:text-primary">
              oddsjam.com
            </a>{" "}
            to upgrade.
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertTitle>Error fetching arbitrage</AlertTitle>
        <AlertDescription>
          The server encountered an error while scanning for opportunities.
          <Button variant="outline" size="sm" className="ml-4" onClick={() => refetch()}>
            Retry
          </Button>
        </AlertDescription>
      </Alert>
    );
  }

  const opps = data?.opportunities ?? [];

  return (
    <div className="space-y-6">

      {/* ── Page header ── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Live Arbitrage</h1>
          <p className="text-sm text-muted-foreground flex items-center gap-2 mt-1">
            <RefreshCw className={`w-3 h-3 ${isFetching ? "animate-spin" : ""}`} />
            Last updated: {formatTimeAgo(data?.fetched_at)} — auto-refreshes every 30s
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <label className="text-xs text-muted-foreground whitespace-nowrap font-medium">
              Bankroll $
            </label>
            <input
              type="number" min="100" step="100"
              value={bankrollInput}
              onChange={(e) => handleBankrollChange(e.target.value)}
              className="w-24 bg-secondary text-foreground text-sm rounded-md px-2 py-1.5 border border-border outline-none focus:ring-1 focus:ring-primary font-mono"
            />
          </div>
          <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isFetching}>
            <RefreshCw className={`w-3 h-3 mr-1.5 ${isFetching ? "animate-spin" : ""}`} />
            Refresh
          </Button>
          <Badge variant="outline" className="bg-secondary font-mono">
            {data?.total ?? 0} opportunities
          </Badge>
        </div>
      </div>

      {/* ── Empty state ── */}
      {opps.length === 0 ? (
        <Card className="bg-card border-dashed">
          <CardContent className="flex flex-col items-center justify-center p-12 text-muted-foreground">
            <Info className="w-8 h-8 mb-4 opacity-50" />
            <p>No profitable arbitrage opportunities found right now.</p>
            <p className="text-xs mt-2 opacity-50">Auto-refreshing every 30 seconds…</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
          {opps.map((opp, i) => {
            const betSizes    = getParsedBets(opp);
            const displays    = getDisplayValues(opp);
            const totalStaked = betSizes.reduce((s, b) => s + b, 0);
            const marketDetail = getMarketDetail(opp.market, opp.legs);

            return (
              <Card key={i} className="bg-card border-border overflow-hidden flex flex-col">

                {/* ── Game header ── */}
                <div className="px-4 pt-4 pb-3 border-b border-border">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <div className="font-semibold leading-tight text-base">
                        {opp.home_team} vs {opp.away_team}
                      </div>
                      <div className="flex flex-wrap items-center gap-1.5 mt-1.5">
                        <span className="text-xs uppercase tracking-wider text-muted-foreground font-medium">
                          {opp.sport_key}
                        </span>
                        <span className="text-border text-xs">•</span>
                        <span className="text-xs text-foreground/80 font-semibold">
                          {marketDetail}
                        </span>
                      </div>
                    </div>
                    <Badge
                      variant="outline"
                      className={`font-mono font-bold text-sm shrink-0 ${marginColor(opp.margin_pct)}`}
                    >
                      +{opp.margin_pct.toFixed(2)}%
                    </Badge>
                  </div>

                  {/* Bet position legend strip */}
                  <div className="flex gap-2 mt-3">
                    {opp.legs.map((leg, j) => {
                      const c = betColor(j);
                      return (
                        <div key={j} className={`flex items-center gap-1.5 px-2 py-1 rounded-full border text-xs font-semibold ${c.badge}`}>
                          <span className={`w-2 h-2 rounded-full ${c.dot}`} />
                          Bet {j + 1} → {leg.book}
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* ── Individual bet instructions ── */}
                <CardContent className="p-3 flex-1 space-y-3">
                  {opp.legs.map((leg, j) => {
                    const c       = betColor(j);
                    const profit  = calcProfitIfWins(opp.legs, betSizes, j);
                    const lineStr = leg.line != null
                      ? ` (${leg.line > 0 ? `+${leg.line}` : leg.line})`
                      : "";

                    return (
                      <div
                        key={j}
                        className={`rounded-lg border border-border border-l-4 ${c.strip} bg-secondary/20 overflow-hidden`}
                      >
                        {/* Bet number + book */}
                        <div className={`flex items-center justify-between px-3 py-2 bg-secondary/40 border-b border-border`}>
                          <div className="flex items-center gap-2">
                            <span className={`text-xs font-bold uppercase tracking-widest ${c.book}`}>
                              BET {j + 1} of {opp.legs.length}
                            </span>
                          </div>
                          <div className={`flex items-center gap-1 text-xs font-bold ${c.book}`}>
                            <MapPin className="w-3 h-3" />
                            {leg.book}
                          </div>
                        </div>

                        {/* Selection + odds */}
                        <div className="px-3 py-2 flex items-center justify-between gap-2">
                          <div className="flex-1 min-w-0">
                            <div className="font-semibold text-sm text-foreground">
                              {leg.side}{lineStr}
                            </div>
                            <div className="text-xs text-muted-foreground mt-0.5">
                              at odds{" "}
                              <span className="font-mono font-semibold text-foreground">
                                {formatOdds(leg.price)}
                              </span>
                            </div>
                          </div>
                        </div>

                        {/* Stake input + profit */}
                        <div className="px-3 pb-3 flex items-end gap-3">
                          <div className="flex-1">
                            <label className="text-xs text-muted-foreground font-medium mb-1 block">
                              Stake ($)
                            </label>
                            <div className="flex items-center gap-1">
                              <span className="text-xs text-muted-foreground">$</span>
                              <input
                                type="number" min="0" step="10"
                                value={displays[j] ?? ""}
                                onChange={(e) =>
                                  handleBetInput(opp.event_id, j, e.target.value, opp)
                                }
                                className={`w-full border rounded-md px-2 py-1.5 text-sm outline-none focus:ring-1 font-mono ${c.input}`}
                              />
                            </div>
                          </div>
                          <div className="text-right shrink-0">
                            <div className="text-xs text-muted-foreground mb-1">
                              Profit if wins
                            </div>
                            <div className={`text-sm font-bold font-mono ${profit >= 0 ? "text-green-400" : "text-red-400"}`}>
                              {profit >= 0 ? "+" : ""}{formatMoney(profit)}
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  })}

                  {/* ── Outcome summary ── */}
                  <div className="rounded-lg border border-border bg-secondary/30 p-3">
                    <div className="flex items-center gap-1.5 mb-2.5">
                      <TrendingUp className="w-3.5 h-3.5 text-muted-foreground" />
                      <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                        Guaranteed Outcome Summary
                      </span>
                    </div>
                    <div className="space-y-2">
                      {opp.legs.map((leg, j) => {
                        const profit  = calcProfitIfWins(opp.legs, betSizes, j);
                        const c       = betColor(j);
                        const lineStr = leg.line != null
                          ? ` (${leg.line > 0 ? `+${leg.line}` : leg.line})`
                          : "";
                        return (
                          <div key={j} className="flex items-center justify-between text-xs gap-2">
                            <div className="flex items-center gap-2 min-w-0">
                              <span className={`w-2 h-2 rounded-full shrink-0 ${c.dot}`} />
                              <span className="text-muted-foreground">
                                If{" "}
                                <span className="text-foreground font-semibold">
                                  {leg.side}{lineStr}
                                </span>{" "}
                                wins
                              </span>
                            </div>
                            <span className={`font-mono font-bold shrink-0 ${profit >= 0 ? "text-green-400" : "text-red-400"}`}>
                              {profit >= 0 ? "+" : ""}{formatMoney(profit)}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                    <div className="flex items-center justify-between text-xs pt-2.5 mt-2.5 border-t border-border">
                      <span className="text-muted-foreground font-medium">Total staked across all books</span>
                      <span className="font-mono font-semibold text-foreground">{formatMoney(totalStaked)}</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
