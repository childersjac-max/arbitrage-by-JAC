import { useState, useMemo } from "react";
import { useGetLineTrackerSlate } from "@workspace/api-client-react";
import { formatPct, formatTimeAgo, formatMoney } from "@/lib/format";
import {
  AlertTriangle,
  Clock,
  AlertCircle,
  ArrowUp,
  ArrowDown,
  ArrowUpDown,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";

type SortKey = "edge_pct" | "ev_pct" | "bet_usd" | "model_prob" | "hours_to_game";
type SortDir = "asc" | "desc";

function SortIcon({
  col,
  active,
  dir,
}: {
  col: string;
  active: string;
  dir: SortDir;
}) {
  if (col !== active) return <ArrowUpDown className="w-3 h-3 ml-1 opacity-40" />;
  return dir === "asc" ? (
    <ArrowUp className="w-3 h-3 ml-1 text-primary" />
  ) : (
    <ArrowDown className="w-3 h-3 ml-1 text-primary" />
  );
}

export default function LineTracker() {
  const { data, isLoading, error, refetch } = useGetLineTrackerSlate();
  const [filterSport, setFilterSport] = useState<string>("ALL");
  const [filterMarket, setFilterMarket] = useState<string>("ALL");
  const [sortKey, setSortKey] = useState<SortKey>("edge_pct");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === "desc" ? "asc" : "desc"));
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  };

  const { sports, markets, filteredBets } = useMemo(() => {
    if (!data?.bets) return { sports: [], markets: [], filteredBets: [] };

    type Bet = (typeof data.bets)[0];
    const get = (b: Bet, k: string): string =>
      ((b as unknown as Record<string, unknown>)[k] as string) ?? "";

    const sports = Array.from(
      new Set(data.bets.map((b) => get(b, "sport")).filter(Boolean)),
    );
    const markets = Array.from(
      new Set(data.bets.map((b) => get(b, "market")).filter(Boolean)),
    );

    const filtered = data.bets.filter((b) => {
      if (filterSport !== "ALL" && get(b, "sport") !== filterSport) return false;
      if (filterMarket !== "ALL" && get(b, "market") !== filterMarket) return false;
      return true;
    });

    const sorted = [...filtered].sort((a, b) => {
      const bets = a as unknown as Record<string, unknown>;
      const betsB = b as unknown as Record<string, unknown>;
      const av = (bets[sortKey] as number) ?? 0;
      const bv = (betsB[sortKey] as number) ?? 0;
      return sortDir === "desc" ? bv - av : av - bv;
    });

    return { sports, markets, filteredBets: sorted };
  }, [data, filterSport, filterMarket, sortKey, sortDir]);

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-[400px] w-full" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertTitle>Error loading slate</AlertTitle>
        <AlertDescription>
          Could not load the line tracker slate from the model repository.
          <Button variant="outline" size="sm" className="ml-4" onClick={() => refetch()}>
            Retry
          </Button>
        </AlertDescription>
      </Alert>
    );
  }

  const thSortable = "px-4 py-3 font-medium text-right cursor-pointer hover:text-foreground transition-colors select-none";
  const thStatic = "px-4 py-3 font-medium";

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Live Bet Slate</h1>
          <p className="text-sm text-muted-foreground flex items-center gap-2 mt-1">
            <Clock className="w-4 h-4" />
            Last updated: {formatTimeAgo(data.fetched_at)}
            <span className="text-muted-foreground/50">•</span>
            <span>
              {filteredBets.length} of {data.total} bets
            </span>
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <select
            className="bg-secondary text-foreground text-sm rounded-md px-3 py-1.5 border border-border outline-none focus:ring-1 focus:ring-primary"
            value={filterSport}
            onChange={(e) => setFilterSport(e.target.value)}
          >
            <option value="ALL">All Sports</option>
            {sports.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
          <select
            className="bg-secondary text-foreground text-sm rounded-md px-3 py-1.5 border border-border outline-none focus:ring-1 focus:ring-primary"
            value={filterMarket}
            onChange={(e) => setFilterMarket(e.target.value)}
          >
            <option value="ALL">All Markets</option>
            {markets.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            Refresh
          </Button>
        </div>
      </div>

      <div className="rounded-md border border-border overflow-hidden bg-card">
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="text-xs text-muted-foreground bg-secondary/50 uppercase border-b border-border">
              <tr>
                <th className={thStatic}>Pick</th>
                <th className={thStatic}>Market</th>
                <th className={thStatic}>Book</th>
                <th className={thStatic + " text-right"}>Odds</th>
                <th
                  className={thSortable}
                  onClick={() => toggleSort("model_prob")}
                >
                  <span className="flex items-center justify-end">
                    Prob
                    <SortIcon col="model_prob" active={sortKey} dir={sortDir} />
                  </span>
                </th>
                <th
                  className={thSortable}
                  onClick={() => toggleSort("edge_pct")}
                >
                  <span className="flex items-center justify-end">
                    Edge %
                    <SortIcon col="edge_pct" active={sortKey} dir={sortDir} />
                  </span>
                </th>
                <th className={thSortable} onClick={() => toggleSort("ev_pct")}>
                  <span className="flex items-center justify-end">
                    EV %
                    <SortIcon col="ev_pct" active={sortKey} dir={sortDir} />
                  </span>
                </th>
                <th
                  className={thSortable}
                  onClick={() => toggleSort("bet_usd")}
                >
                  <span className="flex items-center justify-end">
                    Wager
                    <SortIcon col="bet_usd" active={sortKey} dir={sortDir} />
                  </span>
                </th>
                <th className={thStatic}>Notes</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {filteredBets.length === 0 ? (
                <tr>
                  <td
                    colSpan={9}
                    className="px-4 py-8 text-center text-muted-foreground"
                  >
                    No bets match the current filters.
                  </td>
                </tr>
              ) : (
                filteredBets.map((bet, i) => {
                  const b = bet as unknown as Record<string, unknown>;
                  const edgePct = (b["edge_pct"] as number) ?? 0;
                  const evPct = (b["ev_pct"] as number) ?? 0;
                  const modelProb = b["model_prob"] as number | null;
                  const hoursToGame = b["hours_to_game"] as number | null;
                  return (
                    <tr key={i} className="hover:bg-secondary/20 transition-colors">
                      <td className="px-4 py-3">
                        <div className="font-medium text-foreground">
                          {(b["side"] as string) || "-"}
                        </div>
                        <div className="text-xs text-muted-foreground flex items-center gap-1 mt-0.5">
                          <span className="font-mono">{b["sport"] as string}</span>
                          {hoursToGame != null && (
                            <span
                              className={
                                hoursToGame < 2 ? "text-destructive font-medium" : ""
                              }
                            >
                              • {hoursToGame.toFixed(1)}h
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="font-medium text-foreground">
                          {b["market"] as string}
                        </div>
                        <div className="text-xs text-muted-foreground mt-0.5 font-mono">
                          {b["sport_key"] as string}
                        </div>
                      </td>
                      <td className="px-4 py-3 font-mono text-xs uppercase">
                        {b["book"] as string}
                      </td>
                      <td className="px-4 py-3 text-right font-mono">
                        <div className="text-foreground">
                          {b["american_odds_display"] as string}
                        </div>
                        <div className="text-xs text-muted-foreground mt-0.5">
                          {b["line"] && b["line"] !== "" ? `Line: ${b["line"]}` : ""}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-muted-foreground">
                        {modelProb != null
                          ? `${(modelProb * 100).toFixed(1)}%`
                          : "-"}
                      </td>
                      <td className="px-4 py-3 text-right font-mono">
                        <span
                          className={
                            edgePct > 3
                              ? "text-green-500"
                              : edgePct > 0
                              ? "text-green-400"
                              : "text-muted-foreground"
                          }
                        >
                          {formatPct(b["edge_pct"] as number | null)}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right font-mono">
                        <span className={evPct > 0 ? "text-green-500" : "text-destructive"}>
                          {formatPct(b["ev_pct"] as number | null)}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="font-mono font-medium text-primary">
                          {formatMoney(b["bet_usd"] as number | null)}
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex flex-col gap-1 items-start">
                          {Boolean(b["confidence"]) && (
                            <Badge
                              variant="outline"
                              className="text-[10px] uppercase bg-secondary"
                            >
                              {String(b["confidence"])}
                            </Badge>
                          )}
                          {Boolean(b["is_arb_side"]) && (
                            <Badge
                              variant="outline"
                              className="text-[10px] border-primary text-primary bg-primary/10"
                            >
                              ARB: {String(b["arb_partner_book"] ?? "")}{" "}
                              {String(b["arb_partner_price"] ?? "")}
                            </Badge>
                          )}
                          {Boolean(b["injured_players"]) && (
                            <div
                              className="text-[10px] text-destructive flex items-center gap-1 mt-1 max-w-[150px] truncate"
                              title={String(b["injured_players"])}
                            >
                              <AlertTriangle className="w-3 h-3 flex-shrink-0" />
                              <span className="truncate">
                                {String(b["injured_players"])}
                              </span>
                            </div>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
