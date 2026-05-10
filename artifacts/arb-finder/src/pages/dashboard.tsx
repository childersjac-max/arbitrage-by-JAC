import { useArbitrageOpportunities, useOpportunitiesSummary } from "@/hooks/use-oddsjam";
import { formatPercent, formatDate } from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Activity, Clock, Percent, TrendingUp, DollarSign } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";

// ── Sportsbook logos via Clearbit CDN (fetched by browser, not server) ───────

const G = "https://www.google.com/s2/favicons?domain=";
const BOOK_LOGOS: Record<string, string> = {
  draftkings:  `${G}draftkings.com&sz=64`,
  fanduel:     `${G}fanduel.com&sz=64`,
  betmgm:      `${G}betmgm.com&sz=64`,
  caesars:     `${G}caesars.com&sz=64`,
  bet365:      `${G}bet365.com&sz=64`,
  fanatics:    `${G}fanatics.com&sz=64`,
  thescore:    `${G}thescore.bet&sz=64`,
};

function getBookLogo(bookTitle: string): string | null {
  const key = bookTitle.toLowerCase().replace(/\s+/g, "_").replace(/[^a-z0-9_]/g, "");
  return BOOK_LOGOS[key] ?? null;
}

function BookLogo({ title }: { title: string }) {
  const src = getBookLogo(title);
  if (!src) return (
    <span className="inline-flex items-center justify-center w-5 h-5 rounded bg-secondary text-[9px] font-bold text-muted-foreground shrink-0">
      {title.slice(0, 2).toUpperCase()}
    </span>
  );
  return (
    <img
      src={src}
      alt={title}
      width={20}
      height={20}
      className="rounded object-contain shrink-0 inline-block"
      onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = "none"; }}
    />
  );
}

// ── Clean market label ────────────────────────────────────────────────────────

function cleanMarketLabel(raw: string): string {
  // Strip grouping key suffix (e.g. "moneyline::home" → "moneyline")
  const base = raw.includes("::") ? raw.split("::")[0]! : raw;
  // Strip trailing numeric line (e.g. "spreads_-3.5" → "spreads")
  const clean = base.replace(/_[-+]?\d+\.?\d*$/, "");
  return clean.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function Dashboard() {
  const { data: summary, isLoading: isLoadingSummary } = useOpportunitiesSummary();
  const { data: opportunities, isLoading: isLoadingOpps, error } = useArbitrageOpportunities();

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2">
        <h1 className="text-3xl font-bold tracking-tight">Market Overview</h1>
        <p className="text-muted-foreground">Live arbitrage opportunities automatically refreshed every 30s.</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Opportunities</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold font-mono text-primary" data-testid="summary-total-opps">
              {isLoadingSummary ? <Skeleton className="h-8 w-16" /> : summary?.totalOpportunities || 0}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Profit Margin</CardTitle>
            <Percent className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold font-mono text-primary" data-testid="summary-avg-profit">
              {isLoadingSummary ? <Skeleton className="h-8 w-24" /> : formatPercent(summary?.averageProfitPercent || 0)}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Best Available</CardTitle>
            <TrendingUp className="h-4 w-4 text-success" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold font-mono text-success" data-testid="summary-best-profit">
              {isLoadingSummary ? <Skeleton className="h-8 w-24" /> : formatPercent(summary?.bestProfitPercent || 0)}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Top Sport</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold truncate" data-testid="summary-top-sport">
              {isLoadingSummary ? <Skeleton className="h-8 w-32" /> : (summary?.sportBreakdown?.[0]?.sport || "None")}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-7">
        <Card className="col-span-7 lg:col-span-5">
          <CardHeader>
            <CardTitle>Live Arbitrage Finder</CardTitle>
            <CardDescription>Sorted by maximum guaranteed return</CardDescription>
          </CardHeader>
          <CardContent>
            {error ? (
              <div className="text-center py-10 text-destructive border border-dashed border-destructive/50 rounded-md">
                Failed to load opportunities. Check your API key configuration.
              </div>
            ) : isLoadingOpps ? (
              <div className="space-y-2">
                {[...Array(5)].map((_, i) => <Skeleton key={i} className="h-16 w-full" />)}
              </div>
            ) : opportunities?.length === 0 ? (
              <div className="text-center py-10 text-muted-foreground border border-dashed border-border rounded-md">
                No arbitrage opportunities found. Markets might be tight right now.
              </div>
            ) : (
              <Accordion type="single" collapsible className="w-full space-y-2">
                {opportunities?.map((opp) => (
                  <AccordionItem key={opp.id} value={opp.id} className="border border-border bg-card rounded-md px-4 data-[state=open]:border-primary/50 transition-colors" data-testid={`arb-item-${opp.id}`}>
                    <AccordionTrigger className="hover:no-underline py-4">
                      <div className="flex items-center justify-between w-full pr-4">
                        <div className="flex flex-col items-start gap-1">
                          <div className="flex items-center gap-2">
                            <Badge variant="outline" className="font-mono">{opp.sport}</Badge>
                            <Badge variant="secondary">{cleanMarketLabel(opp.market)}</Badge>
                          </div>
                          <span className="font-semibold text-left">{opp.homeTeam} vs {opp.awayTeam}</span>
                          <span className="text-xs text-muted-foreground flex items-center gap-1">
                            <Clock className="w-3 h-3" /> {formatDate(opp.commenceTime)}
                          </span>
                        </div>
                        <div className="flex flex-col items-end">
                          <span className="text-lg font-bold text-success font-mono" data-testid={`profit-${opp.id}`}>
                            +{opp.profitPercent.toFixed(3)}%
                          </span>
                          <span className="text-xs text-muted-foreground">Guaranteed Profit</span>
                        </div>
                      </div>
                    </AccordionTrigger>
                    <AccordionContent>
                      <div className="pt-2 pb-4">
                        <div className="rounded-md border border-border overflow-hidden">
                          <Table>
                            <TableHeader className="bg-secondary/50">
                              <TableRow>
                                <TableHead>Bookmaker</TableHead>
                                <TableHead>Outcome</TableHead>
                                <TableHead className="text-right">Odds</TableHead>
                                <TableHead className="text-right">Stake ($1000 Total)</TableHead>
                              </TableRow>
                            </TableHeader>
                            <TableBody>
                              {opp.legs.map((leg, i) => (
                                <TableRow key={i}>
                                  <TableCell>
                                    <div className="flex items-center gap-2 font-medium">
                                      <BookLogo title={leg.bookmakerTitle} />
                                      {leg.bookmakerTitle}
                                    </div>
                                  </TableCell>
                                  <TableCell>{leg.outcome}</TableCell>
                                  <TableCell className="text-right font-mono">
                                    {leg.price > 0 && leg.price < 100
                                      ? leg.price.toFixed(2)
                                      : leg.price > 0 ? `+${leg.price}` : leg.price}
                                  </TableCell>
                                  <TableCell className="text-right font-mono text-success">${leg.stake.toFixed(2)}</TableCell>
                                </TableRow>
                              ))}
                            </TableBody>
                          </Table>
                        </div>
                        <div className="mt-2 text-xs text-muted-foreground flex justify-between">
                          <span>Detected: {formatDate(opp.detectedAt)}</span>
                          <span>Total Implied: {(opp.totalImpliedProbability * 100).toFixed(2)}%</span>
                        </div>
                      </div>
                    </AccordionContent>
                  </AccordionItem>
                ))}
              </Accordion>
            )}
          </CardContent>
        </Card>

        <div className="col-span-7 lg:col-span-2 space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Sport Breakdown</CardTitle>
            </CardHeader>
            <CardContent>
              {isLoadingSummary ? (
                <div className="space-y-2">
                  {[...Array(3)].map((_, i) => <Skeleton key={i} className="h-8 w-full" />)}
                </div>
              ) : (
                <div className="space-y-4">
                  {summary?.sportBreakdown?.map(sb => (
                    <div key={sb.sport} className="flex items-center justify-between">
                      <div className="flex flex-col">
                        <span className="text-sm font-medium">{sb.sport}</span>
                        <span className="text-xs text-muted-foreground">{sb.count} opportunities</span>
                      </div>
                      <span className="text-sm font-mono text-success">{formatPercent(sb.avgProfit)} avg</span>
                    </div>
                  ))}
                  {(!summary?.sportBreakdown || summary.sportBreakdown.length === 0) && (
                    <div className="text-sm text-muted-foreground">No data available</div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Market Breakdown</CardTitle>
            </CardHeader>
            <CardContent>
              {isLoadingSummary ? (
                <div className="space-y-2">
                  {[...Array(3)].map((_, i) => <Skeleton key={i} className="h-8 w-full" />)}
                </div>
              ) : (
                <div className="space-y-4">
                  {summary?.marketBreakdown?.map(mb => (
                    <div key={mb.market} className="flex items-center justify-between">
                      <span className="text-sm font-medium">{cleanMarketLabel(mb.market)}</span>
                      <span className="text-sm font-mono">{mb.count}</span>
                    </div>
                  ))}
                  {(!summary?.marketBreakdown || summary.marketBreakdown.length === 0) && (
                    <div className="text-sm text-muted-foreground">No data available</div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
