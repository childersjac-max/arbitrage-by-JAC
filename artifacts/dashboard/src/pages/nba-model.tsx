import {
  useGetNbaModelPredictions,
  useGetNbaModelBacktest,
  useGetNbaModelBetLog,
} from "@workspace/api-client-react";
import { formatPercent, formatOdds, formatTimeAgo } from "@/lib/format";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
} from "recharts";
import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { AlertCircle } from "lucide-react";

interface BetLogEntry {
  id?: string;
  date?: string;
  matchup?: string;
  game?: string;
  side?: string;
  team?: string;
  odds?: number;
  best_book?: string;
  model_prob?: number;
  edge?: number;
  kelly_pct?: number;
  grade?: string;
  result?: string;
  pnl?: number;
}

function SectionError({ label }: { label: string }) {
  return (
    <Alert variant="destructive" className="my-2">
      <AlertCircle className="h-4 w-4" />
      <AlertTitle>Failed to load {label}</AlertTitle>
      <AlertDescription>
        Could not retrieve data from the NBA model repository. Check connectivity or try
        refreshing.
      </AlertDescription>
    </Alert>
  );
}

function StatCard({
  label,
  value,
  loading,
  colored,
}: {
  label: string;
  value: React.ReactNode;
  loading: boolean;
  colored?: boolean;
}) {
  return (
    <Card className="bg-card">
      <CardHeader className="pb-2">
        <CardTitle className="text-xs text-muted-foreground font-medium uppercase tracking-wider">
          {label}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {loading ? (
          <Skeleton className="h-8 w-24" />
        ) : (
          <div className={`text-2xl font-mono font-bold ${colored ?? false ? "" : "text-foreground"}`}>
            {value}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default function NbaModel() {
  const {
    data: predictions,
    isLoading: isLoadingPreds,
    error: predsError,
  } = useGetNbaModelPredictions();
  const {
    data: backtest,
    isLoading: isLoadingBacktest,
    error: backtestError,
  } = useGetNbaModelBacktest();
  const {
    data: betLog,
    isLoading: isLoadingBetLog,
    error: betLogError,
  } = useGetNbaModelBetLog();

  const bt = backtest as Record<string, unknown> | undefined;
  const roiPct = bt?.["roi_pct"] as number | null | undefined;
  const winRate = bt?.["win_rate"] as number | null | undefined;
  const totalPnl = bt?.["total_pnl"] as number | null | undefined;
  const auc = bt?.["auc"] as number | null | undefined;
  const accuracy = bt?.["accuracy"] as number | null | undefined;
  const maxDd = bt?.["max_drawdown_pct"] as number | null | undefined;
  const totalBets = bt?.["total_bets"] as number | null | undefined;
  const bankrollHistory = bt?.["bankroll_history"] as
    | Array<Record<string, unknown>>
    | null
    | undefined;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight">NBA Prediction Model</h1>
        {predictions?.fetched_at && (
          <p className="text-sm text-muted-foreground font-mono">
            Updated {formatTimeAgo(predictions.fetched_at)}
          </p>
        )}
      </div>

      {backtestError ? (
        <SectionError label="backtest metrics" />
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard
            label="ROI"
            loading={isLoadingBacktest}
            value={
              <span className={(roiPct ?? 0) > 0 ? "text-green-500" : "text-destructive"}>
                {roiPct != null ? formatPercent(roiPct) : "-"}
              </span>
            }
          />
          <StatCard
            label="Win Rate"
            loading={isLoadingBacktest}
            value={winRate != null ? formatPercent(winRate) : "-"}
          />
          <StatCard
            label="AUC / Accuracy"
            loading={isLoadingBacktest}
            value={
              <span className="text-lg">
                {auc != null ? auc.toFixed(3) : "-"} /{" "}
                {accuracy != null ? formatPercent(accuracy) : "-"}
              </span>
            }
          />
          <StatCard
            label={`Max Drawdown • ${totalBets ?? "?"} bets`}
            loading={isLoadingBacktest}
            value={
              <span className="text-destructive text-lg">
                {maxDd != null ? formatPercent(maxDd) : "-"}
              </span>
            }
          />
        </div>
      )}

      {!backtestError && !isLoadingBacktest && totalPnl != null && (
        <div className="flex items-center gap-4 text-sm text-muted-foreground font-mono">
          <span>
            P&L:{" "}
            <span className={(totalPnl ?? 0) > 0 ? "text-green-500" : "text-destructive"}>
              {(totalPnl ?? 0) > 0 ? "+" : ""}${totalPnl.toFixed(2)}
            </span>
          </span>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <Card className="bg-card border-border">
            <CardHeader>
              <CardTitle className="text-sm font-medium">Bankroll Equity Curve</CardTitle>
            </CardHeader>
            <CardContent>
              {backtestError ? (
                <SectionError label="equity curve" />
              ) : isLoadingBacktest ? (
                <Skeleton className="h-[300px] w-full" />
              ) : bankrollHistory && bankrollHistory.length > 0 ? (
                <div className="h-[300px] w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart
                      data={bankrollHistory}
                      margin={{ top: 5, right: 5, left: -20, bottom: 0 }}
                    >
                      <XAxis
                        dataKey="game"
                        stroke="#888888"
                        fontSize={10}
                        tickLine={false}
                        axisLine={false}
                        label={{
                          value: "Games",
                          position: "insideBottomRight",
                          offset: -5,
                          fontSize: 10,
                          fill: "#888888",
                        }}
                      />
                      <YAxis
                        stroke="#888888"
                        fontSize={10}
                        tickLine={false}
                        axisLine={false}
                        tickFormatter={(v: number) => `$${v}`}
                      />
                      <RechartsTooltip
                        contentStyle={{
                          backgroundColor: "hsl(var(--card))",
                          border: "1px solid hsl(var(--border))",
                          fontSize: "12px",
                        }}
                        labelStyle={{ color: "hsl(var(--muted-foreground))" }}
                        formatter={(v: unknown) => [`$${Number(v).toFixed(2)}`, "Bankroll"]}
                        labelFormatter={(g: unknown) => `Game ${g}`}
                      />
                      <Line
                        type="monotone"
                        dataKey="value"
                        stroke="hsl(var(--primary))"
                        strokeWidth={2}
                        dot={false}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="h-[300px] flex items-center justify-center text-muted-foreground text-sm">
                  No backtest history available
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="bg-card border-border">
            <CardHeader>
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                Today's Edges
                <Badge variant="secondary" className="ml-auto">
                  {predictions?.total ?? 0} picks
                </Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              {predsError ? (
                <div className="p-4">
                  <SectionError label="today's predictions" />
                </div>
              ) : isLoadingPreds ? (
                <div className="p-6 space-y-4">
                  <Skeleton className="h-10 w-full" />
                  <Skeleton className="h-10 w-full" />
                </div>
              ) : (predictions?.predictions?.length ?? 0) > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm text-left">
                    <thead className="text-xs text-muted-foreground bg-secondary/50 uppercase border-y border-border">
                      <tr>
                        <th className="px-4 py-2 font-medium">Game</th>
                        <th className="px-4 py-2 font-medium">Pick</th>
                        <th className="px-4 py-2 font-medium text-right">Odds</th>
                        <th className="px-4 py-2 font-medium text-right">Model</th>
                        <th className="px-4 py-2 font-medium text-right">Edge</th>
                        <th className="px-4 py-2 font-medium text-right">Kelly</th>
                        <th className="px-4 py-2 font-medium text-center">Grade</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {predictions!.predictions.map((p, i) => {
                        const pp = p as Record<string, unknown>;
                        return (
                          <tr key={i} className="hover:bg-secondary/20">
                            <td className="px-4 py-2">
                              <div className="font-medium">
                                {(pp["matchup"] as string) || (pp["game_id"] as string) || "-"}
                              </div>
                              <div className="text-xs text-muted-foreground">
                                {pp["game_time"] as string}
                              </div>
                            </td>
                            <td className="px-4 py-2">
                              <div className="font-medium">
                                {(pp["label"] as string) ||
                                  `${pp["team"] as string} ${pp["side"] as string}`}
                              </div>
                              {Boolean(pp["reason"]) && (
                                <div
                                  className="text-xs text-muted-foreground truncate max-w-[200px]"
                                  title={String(pp["reason"])}
                                >
                                  {String(pp["reason"])}
                                </div>
                              )}
                            </td>
                            <td className="px-4 py-2 text-right font-mono">
                              {formatOdds(pp["odds"] as number | null)}
                            </td>
                            <td className="px-4 py-2 text-right font-mono">
                              {pp["model_prob"] != null
                                ? formatPercent(pp["model_prob"] as number)
                                : "-"}
                            </td>
                            <td className="px-4 py-2 text-right font-mono text-green-500">
                              {pp["edge"] != null ? formatPercent(pp["edge"] as number) : "-"}
                            </td>
                            <td className="px-4 py-2 text-right font-mono text-muted-foreground">
                              {pp["kelly_pct"] != null
                                ? `${(pp["kelly_pct"] as number).toFixed(1)}%`
                                : "-"}
                            </td>
                            <td className="px-4 py-2 text-center">
                              <Badge
                                variant="outline"
                                className={`font-mono ${
                                  pp["grade"] === "A"
                                    ? "border-green-500 text-green-500"
                                    : pp["grade"] === "B"
                                    ? "border-primary text-primary"
                                    : "border-muted-foreground text-muted-foreground"
                                }`}
                              >
                                {(pp["grade"] as string) ?? "-"}
                              </Badge>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="p-6 text-center text-muted-foreground text-sm">
                  No recommendations available.
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <Card className="bg-card border-border flex flex-col h-[600px]">
            <CardHeader className="flex-none">
              <CardTitle className="text-sm font-medium">
                Bet Log
                {betLog?.bets?.length ? (
                  <span className="ml-2 text-xs text-muted-foreground font-normal">
                    ({betLog.bets.length} entries)
                  </span>
                ) : null}
              </CardTitle>
            </CardHeader>
            <CardContent className="flex-1 overflow-auto p-0">
              {betLogError ? (
                <div className="p-4">
                  <SectionError label="bet log" />
                </div>
              ) : isLoadingBetLog ? (
                <div className="p-4 space-y-4">
                  <Skeleton className="h-8 w-full" />
                  <Skeleton className="h-8 w-full" />
                </div>
              ) : betLog?.bets && betLog.bets.length > 0 ? (
                <table className="w-full text-xs text-left">
                  <thead className="text-muted-foreground bg-secondary/50 uppercase sticky top-0 border-y border-border">
                    <tr>
                      <th className="px-3 py-2 font-medium">Game</th>
                      <th className="px-3 py-2 font-medium">Pick</th>
                      <th className="px-3 py-2 font-medium text-right">Result</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {(betLog.bets as BetLogEntry[]).slice(0, 60).map((b, i) => {
                      const isPending = b.result === "PENDING" || !b.result;
                      const isWin = b.result === "WIN" || b.result === "W";
                      const isLoss = b.result === "LOSS" || b.result === "L";
                      return (
                        <tr key={i} className="hover:bg-secondary/20">
                          <td className="px-3 py-2">
                            <div className="text-muted-foreground whitespace-nowrap">
                              {b.date}
                            </div>
                            <div
                              className="truncate max-w-[80px] text-foreground"
                              title={b.matchup ?? b.game}
                            >
                              {b.matchup ?? b.game}
                            </div>
                          </td>
                          <td className="px-3 py-2">
                            <div className="font-medium truncate max-w-[100px]" title={b.team}>
                              {b.team ?? b.side}
                            </div>
                            <div className="text-muted-foreground">
                              {formatOdds(b.odds ?? null)}
                              {b.best_book ? ` • ${b.best_book}` : ""}
                            </div>
                          </td>
                          <td className="px-3 py-2 text-right">
                            <Badge
                              variant="outline"
                              className={`text-[10px] font-mono ${
                                isPending
                                  ? "border-muted-foreground text-muted-foreground"
                                  : isWin
                                  ? "border-green-500 text-green-500"
                                  : isLoss
                                  ? "border-destructive text-destructive"
                                  : "border-muted-foreground text-muted-foreground"
                              }`}
                            >
                              {b.result ?? "PENDING"}
                            </Badge>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              ) : (
                <div className="p-4 text-center text-muted-foreground text-sm">
                  No bets found.
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
