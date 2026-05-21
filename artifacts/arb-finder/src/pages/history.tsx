import { useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  LabelList,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useHistoryChart } from "@/hooks/use-oddsjam";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { formatPercent } from "@/lib/format";
import { Activity, Clock, Percent, TrendingUp } from "lucide-react";

const RANGE_OPTIONS = [
  { value: "today", label: "Today" },
  { value: "7d", label: "7 Days" },
  { value: "30d", label: "30 Days" },
] as const;

function formatBucketLabel(time: string, bucketUnit: string, label?: string) {
  if (label) return label;
  const d = new Date(time);
  if (bucketUnit === "hour") {
    return d.toLocaleTimeString([], { hour: "numeric", hour12: true });
  }
  return d.toLocaleDateString([], { month: "short", day: "numeric" });
}

export default function HistoryPage() {
  const [range, setRange] = useState<string>("today");
  const [sport, setSport] = useState("all");
  const [league, setLeague] = useState("all");

  const { data, isLoading } = useHistoryChart(range, sport, league);

  const chartData = (data?.buckets ?? []).map((b) => ({
    ...b,
    label: formatBucketLabel(b.time, data?.bucketUnit ?? "hour", b.label),
  }));

  const scatterData = (data?.opportunities ?? []).map((g) => ({
    x: new Date(g.firstSeenAt).getTime(),
    y: g.profitPercent,
    label: `${g.homeTeam} vs ${g.awayTeam}`,
    sport: g.sport,
    market: g.market,
    duration: g.durationMinutes,
  }));

  const sportPills = data?.sportFilters ?? [
    { value: "all", label: "All Sports" },
    { value: "baseball", label: "Baseball" },
    { value: "basketball", label: "Basketball" },
    { value: "wnba", label: "WNBA" },
    { value: "football", label: "Football" },
    { value: "golf", label: "Golf" },
    { value: "hockey", label: "Hockey" },
    { value: "soccer", label: "Soccer" },
  ];

  const showLeague =
    sport === "all" || sport === "basketball" || sport === "soccer";
  const leaguePills = (data?.leagueFilters ?? []).filter((l) => {
    if (l.value === "all") return true;
    if (sport === "basketball") return l.value === "wnba" || l.value === "all";
    if (sport === "soccer")
      return ["mls", "epl", "ucl", "all"].includes(l.value);
    if (sport === "golf" || sport === "all") return l.value === "pga" || l.value === "all";
    return l.value === "all";
  });

  const summary = data?.summary;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2">
        <h1 className="text-3xl font-bold tracking-tight">History</h1>
        <p className="text-muted-foreground">
          Track arbitrage opportunities over time — when they appeared, how long they lasted, and their returns.
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        {RANGE_OPTIONS.map((r) => (
          <button
            key={r.value}
            type="button"
            onClick={() => setRange(r.value)}
            className={cn(
              "px-4 py-1.5 rounded-full text-sm font-medium transition-colors border",
              range === r.value
                ? "bg-primary text-primary-foreground border-primary"
                : "border-border text-muted-foreground hover:text-foreground",
            )}
          >
            {r.label}
          </button>
        ))}
      </div>

      <div className="flex flex-wrap gap-2">
        {sportPills.map((sp) => (
          <button
            key={sp.value}
            type="button"
            onClick={() => {
              setSport(sp.value);
              setLeague("all");
            }}
            className={cn(
              "px-3 py-1 rounded-full text-xs font-medium border transition-colors",
              sport === sp.value
                ? "bg-secondary text-foreground border-foreground/30"
                : "border-border text-muted-foreground hover:text-foreground",
            )}
          >
            {sp.label}
          </button>
        ))}
      </div>

      {showLeague && leaguePills.length > 1 && (
        <div className="flex flex-wrap gap-2">
          {leaguePills.map((l) => (
            <button
              key={l.value}
              type="button"
              onClick={() => setLeague(l.value)}
              className={cn(
                "px-3 py-1 rounded-full text-xs font-medium border transition-colors",
                league === l.value
                  ? "bg-secondary/80 text-foreground"
                  : "border-border/60 text-muted-foreground",
              )}
            >
              {l.label}
            </button>
          ))}
        </div>
      )}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: "TOTAL FOUND", value: summary ? String(summary.totalOpportunities) : null, icon: Activity },
          { label: "AVG PROFIT", value: summary ? formatPercent(summary.avgProfit) : null, icon: Percent },
          { label: "BEST PROFIT", value: summary ? formatPercent(summary.bestProfit) : null, icon: TrendingUp },
          { label: "AVG DURATION", value: summary ? `${summary.avgDurationMinutes}m` : null, icon: Clock },
        ].map((kpi) => (
          <Card key={kpi.label} className="border-l-4 border-l-primary/50">
            <CardHeader className="pb-2 pt-4">
              <CardDescription className="text-[10px] font-semibold tracking-widest uppercase">
                {kpi.label}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {isLoading || kpi.value === null ? (
                <Skeleton className="h-8 w-20" />
              ) : (
                <span className="text-2xl font-bold font-mono">{kpi.value}</span>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Opportunities Over Time</CardTitle>
            <CardDescription>
              Arbs detected per {data?.bucketUnit ?? "hour"}
            </CardDescription>
          </CardHeader>
          <CardContent className="h-[280px]">
            {isLoading ? (
              <Skeleton className="h-full w-full" />
            ) : chartData.length === 0 ? (
              <div className="h-full flex items-center justify-center text-muted-foreground text-sm">
                No data for this period
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 16, right: 8, left: 0, bottom: 4 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" vertical={false} />
                  <XAxis dataKey="label" tick={{ fontSize: 11, fill: "#94a3b8" }} axisLine={false} tickLine={false} />
                  <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: "#94a3b8" }} width={28} axisLine={false} tickLine={false} />
                  <Tooltip
                    contentStyle={{
                      background: "#1e293b",
                      border: "1px solid #334155",
                      borderRadius: 8,
                    }}
                  />
                  <Bar dataKey="count" name="Arbs found" fill="#6366f1" radius={[4, 4, 0, 0]}>
                    <LabelList dataKey="count" position="top" fill="#a5b4fc" fontSize={11} />
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Profit % When Found</CardTitle>
            <CardDescription>Each point is one detected opportunity</CardDescription>
          </CardHeader>
          <CardContent className="h-[280px]">
            {isLoading ? (
              <Skeleton className="h-full w-full" />
            ) : scatterData.length === 0 ? (
              <div className="h-full flex items-center justify-center text-muted-foreground text-sm">
                No opportunities in range
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={scatterData} margin={{ top: 16, right: 12, left: 0, bottom: 4 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                  <XAxis
                    dataKey="x"
                    type="number"
                    domain={["dataMin", "dataMax"]}
                    tickFormatter={(v) =>
                      new Date(v).toLocaleTimeString([], { hour: "numeric", hour12: true })
                    }
                    tick={{ fontSize: 10, fill: "#94a3b8" }}
                  />
                  <YAxis tick={{ fontSize: 11, fill: "#94a3b8" }} unit="%" />
                  <Tooltip
                    labelFormatter={(v) => new Date(Number(v)).toLocaleString()}
                    formatter={(v: number) => [`${v.toFixed(2)}%`, "Profit"]}
                  />
                  <Line type="monotone" dataKey="y" stroke="#34d399" dot={{ r: 3 }} strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Recent Opportunities</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <Skeleton className="h-32 w-full" />
          ) : !data?.opportunities?.length ? (
            <p className="text-sm text-muted-foreground">No opportunities recorded yet.</p>
          ) : (
            <ul className="space-y-2 text-sm">
              {data.opportunities.slice(0, 25).map((o) => (
                <li
                  key={o.oppId}
                  className="flex flex-wrap items-center justify-between gap-2 border-b border-border/50 py-2 last:border-0"
                >
                  <span className="font-medium">
                    {o.homeTeam} vs {o.awayTeam}
                  </span>
                  <span className="text-muted-foreground text-xs">
                    {o.sport}
                    {o.league ? ` · ${o.league}` : ""} · {o.market}
                  </span>
                  <span className="font-mono text-emerald-500">
                    {formatPercent(o.profitPercent)}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
