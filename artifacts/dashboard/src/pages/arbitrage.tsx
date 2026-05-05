import { useState } from "react";
import {
  useGetArbitrageOpportunities,
  getGetArbitrageOpportunitiesQueryKey,
} from "@workspace/api-client-react";
import { formatMoney, formatTimeAgo, formatOdds } from "@/lib/format";
import { Card, CardContent } from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { KeyRound, RefreshCw, Info, AlertCircle, TrendingUp } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

// ── Market label helpers ─────────────────────────────────────────────────────

const MARKET_LABELS: Record<string, string> = {
  moneyline:          "Moneyline",
  "moneyline_3-way":  "3-Way Moneyline",
  point_spread:       "Point Spread",
  total_points:       "Total Points",
  total_goals:        "Total Goals",
  total_rounds:       "Total Rounds",
  h2h:                "Moneyline",
  spreads:            "Spread",
  totals:             "Total",
  "1h_moneyline":     "1st Half Moneyline",
  "1h_spread":        "1st Half Spread",
  "1h_total":         "1st Half Total Points",
  "2h_moneyline":     "2nd Half Moneyline",
  "2h_spread":        "2nd Half Spread",
  "2h_total":         "2nd Half Total Points",
  "1q_moneyline":     "1st Quarter Moneyline",
  "1q_spread":        "1st Quarter Point Spread",
  "1q_total":         "1st Quarter Total Points",
  "2q_moneyline":     "2nd Quarter Moneyline",
  "2q_spread":        "2nd Quarter Point Spread",
  "3q_moneyline":     "3rd Quarter Moneyline",
  "3q_spread":        "3rd Quarter Point Spread",
  "4q_moneyline":     "4th Quarter Moneyline",
  "4q_spread":        "4th Quarter Point Spread",
  "1p_moneyline":     "1st Period Moneyline",
  "2p_moneyline":     "2nd Period Moneyline",
  "3p_moneyline":     "3rd Period Moneyline",
  "1p_total":         "1st Period Total Goals",
  "draw_no_bet":      "Draw No Bet",
  "btts":             "Both Teams to Score",
  "asian_handicap":   "Asian Handicap",
  "alternate_spread": "Alternate Spread",
  "alternate_total":  "Alternate Total",
};

function getMarketLabel(market: string): string {
  // Try direct lookup first
  if (MARKET_LABELS[market]) return MARKET_LABELS[market];
  // Fall back to title-casing with spaces
  return market
    .replace(/_/g, " ")
    .replace(/\b(\d)(h|q|p)\b/gi, (_, n, t) => {
      const period = t.toLowerCase() === "h" ? "Half" : t.toLowerCase() === "q" ? "Quarter" : "Period";
      const ord = n === "1" ? "1st" : n === "2" ? "2nd" : n === "3" ? "3rd" : `${n}th`;
      return `${ord} ${period}`;
    })
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function getMarketDetail(
  market: string,
  legs: Array<{ line?: number | null; side?: string }>,
): string {
  const label = getMarketLabel(market);
  const line = legs[0]?.line;
  if (line != null && market.includes("spread")) {
    return `${label}  (${line > 0 ? `+${line}` : line})`;
  }
  if (line != null && (market.includes("total") || market.includes("totals"))) {
    return `${label}  (O/U ${Math.abs(line)})`;
  }
  return label;
}

// ── Odds / stake math ────────────────────────────────────────────────────────

function americanToDecimal(price: number): number {
  return price >= 100 ? price / 100 + 1 : 100 / Math.abs(price) + 1;
}

function toImplied(price: number): number {
  return price > 0 ? 100 / (price + 100) : -price / (-price + 100);
}

function calcOptimalStakes(
  legs: Array<{ price: number }>,
  bankroll: number,
): number[] {
  const implied = legs.map((l) => toImplied(l.price));
  const total = implied.reduce((a, b) => a + b, 0);
  if (total <= 0) return legs.map(() => bankroll / legs.length);
  return implied.map((imp) => Math.round((bankroll * imp) / total * 100) / 100);
}

function calcProfitIfWins(
  legs: Array<{ price: number }>,
  betSizes: number[],
  winnerIdx: number,
): number {
  const decimal = americanToDecimal(legs[winnerIdx].price);
  const winnerBet = betSizes[winnerIdx] ?? 0;
  const otherBets = betSizes.reduce((s, b, i) => (i !== winnerIdx ? s + b : s), 0);
  return winnerBet * (decimal - 1) - otherBets;
}

// ── Styling ──────────────────────────────────────────────────────────────────

function marginColor(pct: number): string {
  if (pct > 2)  return "border-green-500 text-green-500 bg-green-500/10";
  if (pct > 1)  return "border-yellow-500 text-yellow-500 bg-yellow-500/10";
  return "border-muted-foreground text-muted-foreground";
}

function profitColor(val: number): string {
  return val >= 0 ? "text-green-400" : "text-red-400";
}

// ── Component ────────────────────────────────────────────────────────────────

export default function Arbitrage() {
  const [bankroll, setBankroll]         = useState<number>(10000);
  const [bankrollInput, setBankrollInput] = useState<string>("10000");
  // customBets keyed by opportunity event_id, value is array of string inputs per leg
  const [customBets, setCustomBets]     = useState<Record<string, string[]>>({});

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

  function getOptimalStr(opp: { legs: Array<{ price: number }> }, bankrollVal: number): string[] {
    return calcOptimalStakes(opp.legs, bankrollVal).map((s) => s.toFixed(2));
  }

  function getDisplayValues(opp: { event_id: string; legs: Array<{ price: number }> }): string[] {
    return customBets[opp.event_id] ?? getOptimalStr(opp, bankroll);
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
      const current = prev[eventId] ?? getOptimalStr(opp, bankroll);
      const updated = [...current];
      updated[legIdx] = val;
      return { ...prev, [eventId]: updated };
    });
  }

  // ── Early return states ─────────────────────────────────────────────────

  if (isLoading && !data) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-[200px] w-full" />
        <Skeleton className="h-[200px] w-full" />
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
            Live arbitrage scanning requires an active OddsJam API key. Set the{" "}
            <code className="bg-secondary px-1 py-0.5 rounded text-foreground">
              ODDSJAM_API_KEY
            </code>{" "}
            environment variable to enable this feature.
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
            {data.access_denied_reason ||
              "Your OddsJam plan does not include arbitrage API access."}{" "}
            Visit{" "}
            <a
              href="https://oddsjam.com"
              target="_blank"
              rel="noopener noreferrer"
              className="underline text-foreground hover:text-primary"
            >
              oddsjam.com
            </a>{" "}
            to upgrade your subscription and unlock live arbitrage scanning.
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
      {/* ── Header ── */}
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
              type="number"
              min="100"
              step="100"
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
            <p className="text-xs mt-2 opacity-50">Auto-refreshing every 30 seconds...</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {opps.map((opp, i) => {
            const betSizes  = getParsedBets(opp);
            const displays  = getDisplayValues(opp);
            const marketDetail = getMarketDetail(opp.market, opp.legs);
            const totalStaked  = betSizes.reduce((s, b) => s + b, 0);

            return (
              <Card key={i} className="bg-card border-border overflow-hidden flex flex-col">

                {/* ── RED BOX: Game + detailed market ── */}
                <div className="p-4 border-b border-border bg-secondary/20 flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <div className="font-semibold leading-tight">
                      {opp.home_team} vs {opp.away_team}
                    </div>
                    <div className="text-xs text-muted-foreground flex flex-wrap items-center gap-1.5 mt-1.5">
                      <span className="uppercase tracking-wider font-medium">{opp.sport_key}</span>
                      <span className="text-border">•</span>
                      <span className="text-foreground/80 font-medium">{marketDetail}</span>
                    </div>
                  </div>
                  <Badge
                    variant="outline"
                    className={`font-mono font-bold text-sm shrink-0 ${marginColor(opp.margin_pct)}`}
                  >
                    +{opp.margin_pct.toFixed(2)}%
                  </Badge>
                </div>

                {/* ── YELLOW BOXES: Legs with bet size inputs ── */}
                <CardContent className="p-0 flex-1">
                  <div className="divide-y divide-border">
                    {opp.legs.map((leg, j) => {
                      const profit = calcProfitIfWins(opp.legs, betSizes, j);
                      const lineStr = leg.line != null
                        ? ` ${leg.line > 0 ? `+${leg.line}` : leg.line}`
                        : "";
                      return (
                        <div key={j} className="px-4 py-3 flex items-center gap-3">
                          {/* Outcome + book */}
                          <div className="flex-1 min-w-0">
                            <div className="font-medium text-sm truncate">
                              {leg.side}{lineStr}
                            </div>
                            <div className="text-xs text-muted-foreground uppercase tracking-wide mt-0.5">
                              {leg.book}
                            </div>
                          </div>

                          {/* Odds */}
                          <div className="font-mono text-sm shrink-0 w-14 text-right">
                            {formatOdds(leg.price)}
                          </div>

                          {/* YELLOW: bet size input */}
                          <div className="flex flex-col items-end gap-1 shrink-0">
                            <div className="flex items-center gap-1">
                              <span className="text-xs text-muted-foreground">$</span>
                              <input
                                type="number"
                                min="0"
                                step="10"
                                value={displays[j] ?? ""}
                                onChange={(e) =>
                                  handleBetInput(opp.event_id, j, e.target.value, opp)
                                }
                                className="w-20 bg-yellow-500/10 border border-yellow-500/40 text-yellow-300 text-sm rounded-md px-2 py-1 outline-none focus:ring-1 focus:ring-yellow-500 font-mono text-right"
                              />
                            </div>
                            <div className={`text-xs font-mono font-semibold ${profitColor(profit)}`}>
                              {profit >= 0 ? "+" : ""}
                              {formatMoney(profit)} if wins
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  {/* ── Outcome summary ── */}
                  <div className="mx-4 mb-4 mt-2 rounded-md border border-border bg-secondary/30 p-3">
                    <div className="flex items-center gap-1.5 mb-2">
                      <TrendingUp className="w-3.5 h-3.5 text-muted-foreground" />
                      <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                        Outcome Summary
                      </span>
                    </div>
                    <div className="space-y-1.5">
                      {opp.legs.map((leg, j) => {
                        const profit = calcProfitIfWins(opp.legs, betSizes, j);
                        const lineStr = leg.line != null
                          ? ` ${leg.line > 0 ? `+${leg.line}` : leg.line}`
                          : "";
                        return (
                          <div key={j} className="flex items-center justify-between text-xs">
                            <span className="text-muted-foreground truncate mr-2">
                              If <span className="text-foreground font-medium">{leg.side}{lineStr}</span> wins
                            </span>
                            <span className={`font-mono font-bold shrink-0 ${profitColor(profit)}`}>
                              {profit >= 0 ? "+" : ""}{formatMoney(profit)}
                            </span>
                          </div>
                        );
                      })}
                      <div className="flex items-center justify-between text-xs pt-1.5 border-t border-border mt-1.5">
                        <span className="text-muted-foreground">Total staked</span>
                        <span className="font-mono text-foreground">{formatMoney(totalStaked)}</span>
                      </div>
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
