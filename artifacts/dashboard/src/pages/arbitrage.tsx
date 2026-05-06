import { useState, useEffect, useRef } from "react";
import {
  useGetArbitrageOpportunities,
  getGetArbitrageOpportunitiesQueryKey,
} from "@workspace/api-client-react";
import { formatMoney, formatTimeAgo } from "@/lib/format";
import { useSelectedDate, isSameDay } from "@/lib/date-context";
import { Card, CardContent } from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { KeyRound, RefreshCw, Info, AlertCircle, Bell, BellOff } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

function marginColor(pct: number) {
  if (pct > 2) return "border-green-500 text-green-500 bg-green-500/10";
  if (pct > 1) return "border-yellow-500 text-yellow-500 bg-yellow-500/10";
  return "border-muted-foreground text-muted-foreground";
}

function calcStakes(price: number, bankroll: number, oppPrice: number): number {
  const toImplied = (p: number) =>
    p > 0 ? 100 / (p + 100) : -p / (-p + 100);
  const imp1 = toImplied(price);
  const imp2 = toImplied(oppPrice);
  const total = imp1 + imp2;
  if (total <= 0) return bankroll / 2;
  return Math.round((imp1 / total) * bankroll * 100) / 100;
}

function useArbNotifications(
  opportunities: Array<{ event_id: string; market: string; margin_pct: number; home_team: string; away_team: string }> | undefined,
) {
  const notifiedRef = useRef<Set<string>>(new Set());
  const [notifEnabled, setNotifEnabled] = useState<boolean>(
    typeof Notification !== "undefined" && Notification.permission === "granted",
  );

  const requestPermission = async () => {
    if (typeof Notification === "undefined") return;
    const perm = await Notification.requestPermission();
    setNotifEnabled(perm === "granted");
  };

  useEffect(() => {
    if (!opportunities || !notifEnabled) return;
    const high = opportunities.filter((o) => o.margin_pct > 1);
    high.forEach((opp) => {
      const key = `${opp.event_id}-${opp.market}-${opp.margin_pct.toFixed(2)}`;
      if (!notifiedRef.current.has(key)) {
        notifiedRef.current.add(key);
        new Notification(`ARB +${opp.margin_pct.toFixed(2)}% — ${opp.home_team} vs ${opp.away_team}`, {
          body: `Market: ${opp.market}. Open the app to view stakes.`,
          icon: "/favicon.ico",
        });
      }
    });
  }, [opportunities, notifEnabled]);

  return { notifEnabled, requestPermission };
}

export default function Arbitrage() {
  const [bankroll, setBankroll] = useState<number>(10000);
  const [bankrollInput, setBankrollInput] = useState<string>("10000");
  const { selectedDate } = useSelectedDate();

  const { data, isLoading, error, refetch, isFetching } = useGetArbitrageOpportunities(
    undefined,
    {
      query: {
        queryKey: getGetArbitrageOpportunitiesQueryKey(),
        refetchInterval: 30000,
      },
    },
  );

  const allOpps = (data?.opportunities ?? []).slice().sort(
    (a, b) => b.margin_pct - a.margin_pct,
  );

  const filteredOpps = allOpps.filter((opp) => {
    if (!opp.commence_time) return true;
    const gameDate = new Date(opp.commence_time);
    return isSameDay(gameDate, selectedDate);
  });

  const { notifEnabled, requestPermission } = useArbNotifications(filteredOpps);

  const handleBankrollChange = (val: string) => {
    setBankrollInput(val);
    const n = parseFloat(val);
    if (!isNaN(n) && n > 0) setBankroll(n);
  };

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
            environment variable in your Replit Secrets to enable this feature.
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

  if (error && !data) {
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

  const dateLabel = selectedDate.toLocaleDateString("en-US", {
    weekday: "long",
    month: "short",
    day: "numeric",
  });

  return (
    <div className="space-y-6">
      {error && data && (
        <Alert variant="destructive" className="py-2">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription className="text-xs">
            Refresh failed — showing last known data.{" "}
            <button className="underline" onClick={() => refetch()}>Try again</button>
          </AlertDescription>
        </Alert>
      )}

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            Live Arbitrage
            <span className="ml-3 text-base font-normal text-muted-foreground">{dateLabel}</span>
          </h1>
          <p className="text-sm text-muted-foreground flex items-center gap-2 mt-1">
            <RefreshCw className={`w-3 h-3 ${isFetching ? "animate-spin" : ""}`} />
            Last updated: {formatTimeAgo(data?.fetched_at)} — auto-refreshes every 30s
          </p>
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          <button
            onClick={requestPermission}
            title={notifEnabled ? "Notifications on" : "Enable arb alerts"}
            className={`p-1.5 rounded transition-colors ${
              notifEnabled
                ? "text-green-500 hover:bg-green-500/10"
                : "text-muted-foreground hover:bg-secondary"
            }`}
          >
            {notifEnabled ? <Bell className="w-4 h-4" /> : <BellOff className="w-4 h-4" />}
          </button>
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
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            disabled={isFetching}
          >
            <RefreshCw className={`w-3 h-3 mr-1.5 ${isFetching ? "animate-spin" : ""}`} />
            Refresh
          </Button>
          <Badge variant="outline" className="bg-secondary font-mono">
            {filteredOpps.length} / {allOpps.length} opps
          </Badge>
        </div>
      </div>

      {filteredOpps.length === 0 ? (
        <Card className="bg-card border-dashed">
          <CardContent className="flex flex-col items-center justify-center p-12 text-muted-foreground">
            <Info className="w-8 h-8 mb-4 opacity-50" />
            <p>No profitable arbitrage opportunities for {dateLabel}.</p>
            <p className="text-xs mt-2 opacity-50">Auto-refreshing every 30 seconds...</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {filteredOpps.map((opp, i) => {
            const prices = opp.legs.map((l) => l.price);
            const stakes =
              opp.legs.length === 2
                ? [
                    calcStakes(prices[0], bankroll, prices[1]),
                    calcStakes(prices[1], bankroll, prices[0]),
                  ]
                : opp.legs.map((l) => l.stake ?? null);

            return (
              <Card
                key={i}
                className="bg-card border-border overflow-hidden flex flex-col"
              >
                <div className="p-4 border-b border-border bg-secondary/20 flex items-start justify-between">
                  <div>
                    <div className="font-semibold">
                      {opp.home_team} vs {opp.away_team}
                    </div>
                    <div className="text-xs text-muted-foreground flex items-center gap-2 mt-1">
                      <span className="uppercase tracking-wider">{opp.sport_key}</span>
                      <span>•</span>
                      <span className="capitalize">{opp.market}</span>
                      {opp.commence_time && (
                        <>
                          <span>•</span>
                          <span>
                            {new Date(opp.commence_time).toLocaleTimeString("en-US", {
                              hour: "numeric",
                              minute: "2-digit",
                            })}
                          </span>
                        </>
                      )}
                    </div>
                  </div>
                  <Badge
                    variant="outline"
                    className={`font-mono font-bold text-sm ml-2 shrink-0 ${marginColor(opp.margin_pct)}`}
                  >
                    +{opp.margin_pct.toFixed(2)}%
                  </Badge>
                </div>
                <div className="p-0 flex-1">
                  <table className="w-full text-sm">
                    <tbody className="divide-y divide-border">
                      {opp.legs.map((leg, j) => (
                        <tr key={j} className="hover:bg-secondary/10">
                          <td className="px-4 py-3">
                            <div className="font-medium">
                              {leg.side}
                              {leg.line != null
                                ? ` ${leg.line > 0 ? `+${leg.line}` : leg.line}`
                                : ""}
                            </div>
                            <div className="text-xs text-muted-foreground uppercase">
                              {leg.book}
                            </div>
                          </td>
                          <td className="px-4 py-3 text-right">
                            <div className="font-mono">
                              {leg.price > 0 ? `+${leg.price}` : leg.price}
                            </div>
                          </td>
                          <td className="px-4 py-3 text-right">
                            {stakes[j] != null && (
                              <div className="font-mono text-primary bg-primary/10 px-2 py-1 rounded inline-block text-xs font-semibold">
                                {formatMoney(stakes[j])}
                              </div>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
