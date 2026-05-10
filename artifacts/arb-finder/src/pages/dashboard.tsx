import { useArbitrageOpportunities, useOpportunitiesSummary } from "@/hooks/use-oddsjam";
import { formatPercent, formatDate } from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Activity, Clock, ExternalLink, Percent, TrendingUp, DollarSign } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";

// ── Sportsbook logos ──────────────────────────────────────────────────────────

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

// ── Sportsbook deep links by sport ───────────────────────────────────────────

const BOOK_URLS: Record<string, Record<string, string>> = {
  draftkings: {
    football:   "https://sportsbook.draftkings.com/leagues/football/nfl",
    basketball: "https://sportsbook.draftkings.com/leagues/basketball/nba",
    baseball:   "https://sportsbook.draftkings.com/leagues/baseball/mlb",
    hockey:     "https://sportsbook.draftkings.com/leagues/hockey/nhl",
    soccer:     "https://sportsbook.draftkings.com/sport/soccer",
    tennis:     "https://sportsbook.draftkings.com/sport/tennis",
    mma:        "https://sportsbook.draftkings.com/sport/mma",
    default:    "https://sportsbook.draftkings.com",
  },
  fanduel: {
    football:   "https://sportsbook.fanduel.com/football/nfl",
    basketball: "https://sportsbook.fanduel.com/basketball/nba",
    baseball:   "https://sportsbook.fanduel.com/baseball/mlb",
    hockey:     "https://sportsbook.fanduel.com/hockey/nhl",
    soccer:     "https://sportsbook.fanduel.com/soccer",
    tennis:     "https://sportsbook.fanduel.com/tennis",
    mma:        "https://sportsbook.fanduel.com/mma",
    default:    "https://sportsbook.fanduel.com",
  },
  betmgm: {
    football:   "https://sports.betmgm.com/en/sports/football-11/betting/usa/nfl-35",
    basketball: "https://sports.betmgm.com/en/sports/basketball-7/betting/usa/nba-6004",
    baseball:   "https://sports.betmgm.com/en/sports/baseball-23/betting/usa/mlb-75",
    hockey:     "https://sports.betmgm.com/en/sports/ice-hockey-19/betting/usa/nhl-41",
    soccer:     "https://sports.betmgm.com/en/sports/soccer-4/betting",
    default:    "https://sports.betmgm.com/en/sports",
  },
  caesars: {
    football:   "https://sportsbook.caesars.com/us/nc/bet/sports/american-football",
    basketball: "https://sportsbook.caesars.com/us/nc/bet/sports/basketball",
    baseball:   "https://sportsbook.caesars.com/us/nc/bet/sports/baseball",
    hockey:     "https://sportsbook.caesars.com/us/nc/bet/sports/ice-hockey",
    soccer:     "https://sportsbook.caesars.com/us/nc/bet/sports/soccer",
    mma:        "https://sportsbook.caesars.com/us/nc/bet/sports/mma",
    default:    "https://sportsbook.caesars.com/us/nc/bet",
  },
  bet365: {
    football:   "https://www.bet365.com/#/AS/B4/",
    basketball: "https://www.bet365.com/#/AS/B6/",
    baseball:   "https://www.bet365.com/#/AS/B18/",
    hockey:     "https://www.bet365.com/#/AS/B17/",
    soccer:     "https://www.bet365.com/#/AS/B1/",
    tennis:     "https://www.bet365.com/#/AS/B13/",
    default:    "https://www.bet365.com",
  },
  fanatics: {
    football:   "https://sportsbook.fanatics.com/sports/football",
    basketball: "https://sportsbook.fanatics.com/sports/basketball",
    baseball:   "https://sportsbook.fanatics.com/sports/baseball",
    hockey:     "https://sportsbook.fanatics.com/sports/hockey",
    soccer:     "https://sportsbook.fanatics.com/sports/soccer",
    default:    "https://sportsbook.fanatics.com",
  },
  thescore: {
    football:   "https://www.thescore.bet/sports/american-football",
    basketball: "https://www.thescore.bet/sports/basketball",
    baseball:   "https://www.thescore.bet/sports/baseball",
    hockey:     "https://www.thescore.bet/sports/ice-hockey",
    soccer:     "https://www.thescore.bet/sports/soccer",
    default:    "https://www.thescore.bet",
  },
};

function getBookUrl(bookTitle: string, sport: string): string {
  const key = bookTitle.toLowerCase().replace(/\s+/g, "_").replace(/[^a-z0-9_]/g, "");
  const urls = BOOK_URLS[key];
  if (!urls) return "#";
  return urls[sport] ?? urls["default"] ?? "#";
}

function getBookLogo(bookTitle: string): string | null {
  const key = bookTitle.toLowerCase().replace(/\s+/g, "_").replace(/[^a-z0-9_]/g, "");
  return BOOK_LOGOS[key] ?? null;
}

function BookLogo({ title }: { title: string }) {
  const src = getBookLogo(title);
  if (!src) return (
    <span className="inline-flex items-center justify-center w-7 h-7 rounded bg-secondary text-[9px] font-bold text-muted-foreground shrink-0">
      {title.slice(0, 2).toUpperCase()}
    </span>
  );
  return (
    <img src={src} alt={title} width={28} height={28}
      className="rounded object-contain shrink-0"
      onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = "none"; }}
    />
  );
}

// ── Bet type helpers ──────────────────────────────────────────────────────────

function getBetType(market: string): string {
  const base = market.includes("::") ? market.split("::")[0]! : market;
  if (base.startsWith("alternate_player_")) return "Alt Prop";
  if (base.startsWith("player_"))           return "Player Prop";
  if (base === "alternate_spread" || base === "alternate_point_spread") return "Alt Spread";
  if (base === "alternate_total" || base.startsWith("alternate_total_")) return "Alt Total";
  if (base === "moneyline" || base === "moneyline_3-way") return "Moneyline";
  if (base === "point_spread")              return "Spread";
  if (base === "total_points" || base === "total_goals" || base === "total_rounds") return "Total";
  return base.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function betTypeColor(type: string): string {
  if (type === "Moneyline")                          return "border-blue-500/60 text-blue-400 bg-blue-500/10";
  if (type === "Spread" || type === "Alt Spread")    return "border-purple-500/60 text-purple-400 bg-purple-500/10";
  if (type === "Total" || type === "Alt Total")      return "border-orange-500/60 text-orange-400 bg-orange-500/10";
  if (type === "Player Prop" || type === "Alt Prop") return "border-pink-500/60 text-pink-400 bg-pink-500/10";
  return "border-muted-foreground text-muted-foreground";
}

function formatOdds(price: number): string {
  if (price > 0 && price < 100) return price.toFixed(2);
  return price > 0 ? `+${price}` : `${price}`;
}

function cleanMarketLabel(raw: string): string {
  const base = raw.includes("::") ? raw.split("::")[0]! : raw;
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

      {/* ── Summary stats ── */}
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
        {/* ── Arb list ── */}
        <Card className="col-span-7 lg:col-span-5">
          <CardHeader>
            <CardTitle>Live Arbitrage Finder</CardTitle>
            <CardDescription>Sorted by guaranteed return — click a row to see exact bet instructions</CardDescription>
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
                {opportunities?.map((opp) => {
                  const betType = getBetType(opp.market);
                  const totalStake = opp.legs.reduce((s, l) => s + l.stake, 0);
                  const guaranteedReturn = opp.legs[0]
                    ? opp.legs[0].stake * (opp.legs[0].price > 0
                        ? (opp.legs[0].price / 100 + 1)
                        : (100 / Math.abs(opp.legs[0].price) + 1))
                    : totalStake * (1 + opp.profitPercent / 100);

                  return (
                    <AccordionItem
                      key={opp.id}
                      value={opp.id}
                      className="border border-border bg-card rounded-md px-4 data-[state=open]:border-primary/50 transition-colors"
                      data-testid={`arb-item-${opp.id}`}
                    >
                      <AccordionTrigger className="hover:no-underline py-4">
                        <div className="flex items-center justify-between w-full pr-4">
                          <div className="flex flex-col items-start gap-1">
                            <div className="flex items-center gap-2 flex-wrap">
                              <Badge variant="outline" className="font-mono text-xs">{opp.sport}</Badge>
                              <Badge variant="outline" className={`text-xs ${betTypeColor(betType)}`}>{betType}</Badge>
                            </div>
                            <span className="font-semibold text-left">{opp.homeTeam} vs {opp.awayTeam}</span>
                            <span className="text-xs text-muted-foreground flex items-center gap-1">
                              <Clock className="w-3 h-3" /> {formatDate(opp.commenceTime)}
                            </span>
                          </div>
                          <div className="flex flex-col items-end gap-0.5">
                            <span className="text-lg font-bold text-success font-mono" data-testid={`profit-${opp.id}`}>
                              +{opp.profitPercent.toFixed(3)}%
                            </span>
                            <span className="text-xs text-muted-foreground">guaranteed profit</span>
                            <span className="text-xs font-mono text-muted-foreground">
                              Bet ${totalStake.toFixed(2)} → Return ${guaranteedReturn.toFixed(2)}
                            </span>
                          </div>
                        </div>
                      </AccordionTrigger>

                      <AccordionContent>
                        <div className="pt-2 pb-4 space-y-3">
                          {/* Bet instructions — one card per leg */}
                          {opp.legs.map((leg, i) => (
                            <div
                              key={i}
                              className="rounded-lg border border-border bg-secondary/20 p-4 flex flex-col sm:flex-row sm:items-center gap-4"
                            >
                              {/* Step number */}
                              <div className="flex items-center justify-center w-9 h-9 rounded-full bg-primary/10 text-primary font-bold text-sm shrink-0 self-start sm:self-center">
                                {i + 1}
                              </div>

                              {/* Sportsbook */}
                              <div className="flex items-center gap-2 min-w-[140px]">
                                <BookLogo title={leg.bookmakerTitle} />
                                <div className="flex flex-col">
                                  <span className="font-bold text-sm">{leg.bookmakerTitle}</span>
                                  <a
                                    href={getBookUrl(leg.bookmakerTitle, opp.sport)}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    onClick={(e) => e.stopPropagation()}
                                    className="inline-flex items-center gap-1 text-xs text-primary hover:underline font-bold mt-0.5"
                                  >
                                    Open & Bet <ExternalLink className="w-3 h-3" />
                                  </a>
                                </div>
                              </div>

                              {/* Divider */}
                              <div className="hidden sm:block w-px h-10 bg-border shrink-0" />

                              {/* Bet details */}
                              <div className="flex-1 flex flex-col gap-0.5">
                                <div className="flex items-center gap-2 flex-wrap">
                                  <Badge variant="outline" className={`text-xs ${betTypeColor(betType)}`}>{betType}</Badge>
                                  <span className="text-xs text-muted-foreground">→</span>
                                  <span className="font-semibold text-sm">{leg.outcome}</span>
                                </div>
                                <p className="text-xs text-muted-foreground mt-1">
                                  Bet <span className="font-mono font-semibold text-foreground">${leg.stake.toFixed(2)}</span> at odds{" "}
                                  <span className={`font-mono font-bold text-base ${leg.price > 0 ? "text-success" : "text-foreground"}`}>
                                    {formatOdds(leg.price)}
                                  </span>
                                </p>
                              </div>

                              {/* Stake chip */}
                              <div className="flex flex-col items-end sm:items-center shrink-0">
                                <span className="text-xs text-muted-foreground">Stake</span>
                                <span className="font-mono font-bold text-lg text-success">${leg.stake.toFixed(2)}</span>
                              </div>
                            </div>
                          ))}

                          {/* Summary footer */}
                          <div className="flex items-center justify-between px-1 pt-1 text-xs text-muted-foreground">
                            <span>Detected: {formatDate(opp.detectedAt)}</span>
                            <span className="font-mono">
                              Total bet: <span className="text-foreground font-semibold">${totalStake.toFixed(2)}</span>
                              &nbsp;·&nbsp;
                              Implied probability: <span className="text-foreground font-semibold">{(opp.totalImpliedProbability * 100).toFixed(2)}%</span>
                            </span>
                          </div>
                        </div>
                      </AccordionContent>
                    </AccordionItem>
                  );
                })}
              </Accordion>
            )}
          </CardContent>
        </Card>

        {/* ── Sidebar ── */}
        <div className="col-span-7 lg:col-span-2 space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Sport Breakdown</CardTitle>
            </CardHeader>
            <CardContent>
              {isLoadingSummary ? (
                <div className="space-y-2">{[...Array(3)].map((_, i) => <Skeleton key={i} className="h-8 w-full" />)}</div>
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
                <div className="space-y-2">{[...Array(3)].map((_, i) => <Skeleton key={i} className="h-8 w-full" />)}</div>
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
