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

// ── Sportsbook logos (Clearbit CDN — fetched by user browser) ────────────────

const BOOK_LOGOS: Record<string, string> = {
  draftkings:   "https://logo.clearbit.com/draftkings.com",
  fanduel:      "https://logo.clearbit.com/fanduel.com",
  betmgm:       "https://logo.clearbit.com/betmgm.com",
  caesars:      "https://logo.clearbit.com/caesars.com",
  bet365:       "https://logo.clearbit.com/bet365.com",
  fanatics:     "https://logo.clearbit.com/fanatics.com",
  hard_rock:    "https://logo.clearbit.com/hardrock.bet",
  betrivers:    "https://logo.clearbit.com/betrivers.com",
  betparx:      "https://logo.clearbit.com/betparx.com",
  pointsbet:    "https://logo.clearbit.com/pointsbet.com",
  barstool:     "https://logo.clearbit.com/barstoolsports.com",
  williamhill:  "https://logo.clearbit.com/williamhill.com",
  superbook:    "https://logo.clearbit.com/superbook.com",
  unibet:       "https://logo.clearbit.com/unibet.com",
  betonline:    "https://logo.clearbit.com/betonline.ag",
  mybookie:     "https://logo.clearbit.com/mybookie.ag",
  bovada:       "https://logo.clearbit.com/bovada.lv",
  espnbet:      "https://logo.clearbit.com/espnbet.com",
  fliff:        "https://logo.clearbit.com/getfliff.com",
  pinnacle:     "https://logo.clearbit.com/pinnacle.com",
};

function getBookLogo(bookTitle: string): string | null {
  const key = bookTitle.toLowerCase().replace(/\s+/g, "_").replace(/[^a-z0-9_]/g, "");
  return BOOK_LOGOS[key] ?? null;
}

// ── Team logos (ESPN CDN) ────────────────────────────────────────────────────

const ESPN_BASE = "https://a.espncdn.com/i/teamlogos";

const TEAM_LOGOS: Record<string, string> = {
  // ── NBA ──────────────────────────────────────────────────────────────────
  "Atlanta Hawks":              `${ESPN_BASE}/nba/500/atl.png`,
  "Boston Celtics":             `${ESPN_BASE}/nba/500/bos.png`,
  "Brooklyn Nets":              `${ESPN_BASE}/nba/500/bkn.png`,
  "Charlotte Hornets":          `${ESPN_BASE}/nba/500/cha.png`,
  "Chicago Bulls":              `${ESPN_BASE}/nba/500/chi.png`,
  "Cleveland Cavaliers":        `${ESPN_BASE}/nba/500/cle.png`,
  "Dallas Mavericks":           `${ESPN_BASE}/nba/500/dal.png`,
  "Denver Nuggets":             `${ESPN_BASE}/nba/500/den.png`,
  "Detroit Pistons":            `${ESPN_BASE}/nba/500/det.png`,
  "Golden State Warriors":      `${ESPN_BASE}/nba/500/gs.png`,
  "Houston Rockets":            `${ESPN_BASE}/nba/500/hou.png`,
  "Indiana Pacers":             `${ESPN_BASE}/nba/500/ind.png`,
  "Los Angeles Clippers":       `${ESPN_BASE}/nba/500/lac.png`,
  "Los Angeles Lakers":         `${ESPN_BASE}/nba/500/lal.png`,
  "Memphis Grizzlies":          `${ESPN_BASE}/nba/500/mem.png`,
  "Miami Heat":                 `${ESPN_BASE}/nba/500/mia.png`,
  "Milwaukee Bucks":            `${ESPN_BASE}/nba/500/mil.png`,
  "Minnesota Timberwolves":     `${ESPN_BASE}/nba/500/min.png`,
  "New Orleans Pelicans":       `${ESPN_BASE}/nba/500/no.png`,
  "New York Knicks":            `${ESPN_BASE}/nba/500/ny.png`,
  "Oklahoma City Thunder":      `${ESPN_BASE}/nba/500/okc.png`,
  "Orlando Magic":              `${ESPN_BASE}/nba/500/orl.png`,
  "Philadelphia 76ers":         `${ESPN_BASE}/nba/500/phi.png`,
  "Phoenix Suns":               `${ESPN_BASE}/nba/500/phx.png`,
  "Portland Trail Blazers":     `${ESPN_BASE}/nba/500/por.png`,
  "Sacramento Kings":           `${ESPN_BASE}/nba/500/sac.png`,
  "San Antonio Spurs":          `${ESPN_BASE}/nba/500/sa.png`,
  "Toronto Raptors":            `${ESPN_BASE}/nba/500/tor.png`,
  "Utah Jazz":                  `${ESPN_BASE}/nba/500/utah.png`,
  "Washington Wizards":         `${ESPN_BASE}/nba/500/wsh.png`,
  // ── NFL ──────────────────────────────────────────────────────────────────
  "Arizona Cardinals":          `${ESPN_BASE}/nfl/500/ari.png`,
  "Atlanta Falcons":            `${ESPN_BASE}/nfl/500/atl.png`,
  "Baltimore Ravens":           `${ESPN_BASE}/nfl/500/bal.png`,
  "Buffalo Bills":              `${ESPN_BASE}/nfl/500/buf.png`,
  "Carolina Panthers":          `${ESPN_BASE}/nfl/500/car.png`,
  "Chicago Bears":              `${ESPN_BASE}/nfl/500/chi.png`,
  "Cincinnati Bengals":         `${ESPN_BASE}/nfl/500/cin.png`,
  "Cleveland Browns":           `${ESPN_BASE}/nfl/500/cle.png`,
  "Dallas Cowboys":             `${ESPN_BASE}/nfl/500/dal.png`,
  "Denver Broncos":             `${ESPN_BASE}/nfl/500/den.png`,
  "Detroit Lions":              `${ESPN_BASE}/nfl/500/det.png`,
  "Green Bay Packers":          `${ESPN_BASE}/nfl/500/gb.png`,
  "Houston Texans":             `${ESPN_BASE}/nfl/500/hou.png`,
  "Indianapolis Colts":         `${ESPN_BASE}/nfl/500/ind.png`,
  "Jacksonville Jaguars":       `${ESPN_BASE}/nfl/500/jax.png`,
  "Kansas City Chiefs":         `${ESPN_BASE}/nfl/500/kc.png`,
  "Las Vegas Raiders":          `${ESPN_BASE}/nfl/500/lv.png`,
  "Los Angeles Chargers":       `${ESPN_BASE}/nfl/500/lac.png`,
  "Los Angeles Rams":           `${ESPN_BASE}/nfl/500/lar.png`,
  "Miami Dolphins":             `${ESPN_BASE}/nfl/500/mia.png`,
  "Minnesota Vikings":          `${ESPN_BASE}/nfl/500/min.png`,
  "New England Patriots":       `${ESPN_BASE}/nfl/500/ne.png`,
  "New Orleans Saints":         `${ESPN_BASE}/nfl/500/no.png`,
  "New York Giants":            `${ESPN_BASE}/nfl/500/nyg.png`,
  "New York Jets":              `${ESPN_BASE}/nfl/500/nyj.png`,
  "Philadelphia Eagles":        `${ESPN_BASE}/nfl/500/phi.png`,
  "Pittsburgh Steelers":        `${ESPN_BASE}/nfl/500/pit.png`,
  "San Francisco 49ers":        `${ESPN_BASE}/nfl/500/sf.png`,
  "Seattle Seahawks":           `${ESPN_BASE}/nfl/500/sea.png`,
  "Tampa Bay Buccaneers":       `${ESPN_BASE}/nfl/500/tb.png`,
  "Tennessee Titans":           `${ESPN_BASE}/nfl/500/ten.png`,
  "Washington Commanders":      `${ESPN_BASE}/nfl/500/wsh.png`,
  // ── MLB ──────────────────────────────────────────────────────────────────
  "Arizona Diamondbacks":       `${ESPN_BASE}/mlb/500/ari.png`,
  "Atlanta Braves":             `${ESPN_BASE}/mlb/500/atl.png`,
  "Baltimore Orioles":          `${ESPN_BASE}/mlb/500/bal.png`,
  "Boston Red Sox":             `${ESPN_BASE}/mlb/500/bos.png`,
  "Chicago Cubs":               `${ESPN_BASE}/mlb/500/chc.png`,
  "Chicago White Sox":          `${ESPN_BASE}/mlb/500/cws.png`,
  "Cincinnati Reds":            `${ESPN_BASE}/mlb/500/cin.png`,
  "Cleveland Guardians":        `${ESPN_BASE}/mlb/500/cle.png`,
  "Colorado Rockies":           `${ESPN_BASE}/mlb/500/col.png`,
  "Detroit Tigers":             `${ESPN_BASE}/mlb/500/det.png`,
  "Houston Astros":             `${ESPN_BASE}/mlb/500/hou.png`,
  "Kansas City Royals":         `${ESPN_BASE}/mlb/500/kc.png`,
  "Los Angeles Angels":         `${ESPN_BASE}/mlb/500/laa.png`,
  "Los Angeles Dodgers":        `${ESPN_BASE}/mlb/500/lad.png`,
  "Miami Marlins":              `${ESPN_BASE}/mlb/500/mia.png`,
  "Milwaukee Brewers":          `${ESPN_BASE}/mlb/500/mil.png`,
  "Minnesota Twins":            `${ESPN_BASE}/mlb/500/min.png`,
  "New York Mets":              `${ESPN_BASE}/mlb/500/nym.png`,
  "New York Yankees":           `${ESPN_BASE}/mlb/500/nyy.png`,
  "Oakland Athletics":          `${ESPN_BASE}/mlb/500/oak.png`,
  "Philadelphia Phillies":      `${ESPN_BASE}/mlb/500/phi.png`,
  "Pittsburgh Pirates":         `${ESPN_BASE}/mlb/500/pit.png`,
  "San Diego Padres":           `${ESPN_BASE}/mlb/500/sd.png`,
  "San Francisco Giants":       `${ESPN_BASE}/mlb/500/sf.png`,
  "Seattle Mariners":           `${ESPN_BASE}/mlb/500/sea.png`,
  "St. Louis Cardinals":        `${ESPN_BASE}/mlb/500/stl.png`,
  "Tampa Bay Rays":             `${ESPN_BASE}/mlb/500/tb.png`,
  "Texas Rangers":              `${ESPN_BASE}/mlb/500/tex.png`,
  "Toronto Blue Jays":          `${ESPN_BASE}/mlb/500/tor.png`,
  "Washington Nationals":       `${ESPN_BASE}/mlb/500/wsh.png`,
  // ── NHL ──────────────────────────────────────────────────────────────────
  "Anaheim Ducks":              `${ESPN_BASE}/nhl/500/ana.png`,
  "Boston Bruins":              `${ESPN_BASE}/nhl/500/bos.png`,
  "Buffalo Sabres":             `${ESPN_BASE}/nhl/500/buf.png`,
  "Calgary Flames":             `${ESPN_BASE}/nhl/500/cgy.png`,
  "Carolina Hurricanes":        `${ESPN_BASE}/nhl/500/car.png`,
  "Chicago Blackhawks":         `${ESPN_BASE}/nhl/500/chi.png`,
  "Colorado Avalanche":         `${ESPN_BASE}/nhl/500/col.png`,
  "Columbus Blue Jackets":      `${ESPN_BASE}/nhl/500/cbj.png`,
  "Dallas Stars":               `${ESPN_BASE}/nhl/500/dal.png`,
  "Detroit Red Wings":          `${ESPN_BASE}/nhl/500/det.png`,
  "Edmonton Oilers":            `${ESPN_BASE}/nhl/500/edm.png`,
  "Florida Panthers":           `${ESPN_BASE}/nhl/500/fla.png`,
  "Los Angeles Kings":          `${ESPN_BASE}/nhl/500/lak.png`,
  "Minnesota Wild":             `${ESPN_BASE}/nhl/500/min.png`,
  "Montreal Canadiens":         `${ESPN_BASE}/nhl/500/mtl.png`,
  "Nashville Predators":        `${ESPN_BASE}/nhl/500/nsh.png`,
  "New Jersey Devils":          `${ESPN_BASE}/nhl/500/njd.png`,
  "New York Islanders":         `${ESPN_BASE}/nhl/500/nyi.png`,
  "New York Rangers":           `${ESPN_BASE}/nhl/500/nyr.png`,
  "Ottawa Senators":            `${ESPN_BASE}/nhl/500/ott.png`,
  "Philadelphia Flyers":        `${ESPN_BASE}/nhl/500/phi.png`,
  "Pittsburgh Penguins":        `${ESPN_BASE}/nhl/500/pit.png`,
  "San Jose Sharks":            `${ESPN_BASE}/nhl/500/sj.png`,
  "Seattle Kraken":             `${ESPN_BASE}/nhl/500/sea.png`,
  "St. Louis Blues":            `${ESPN_BASE}/nhl/500/stl.png`,
  "Tampa Bay Lightning":        `${ESPN_BASE}/nhl/500/tb.png`,
  "Toronto Maple Leafs":        `${ESPN_BASE}/nhl/500/tor.png`,
  "Utah Hockey Club":           `${ESPN_BASE}/nhl/500/utah.png`,
  "Vancouver Canucks":          `${ESPN_BASE}/nhl/500/van.png`,
  "Vegas Golden Knights":       `${ESPN_BASE}/nhl/500/vgk.png`,
  "Washington Capitals":        `${ESPN_BASE}/nhl/500/wsh.png`,
  "Winnipeg Jets":              `${ESPN_BASE}/nhl/500/wpg.png`,
};

function getTeamLogo(teamName: string): string | null {
  if (!teamName) return null;
  // Exact match
  if (TEAM_LOGOS[teamName]) return TEAM_LOGOS[teamName];
  // Fuzzy: find a key that the team name contains or vice versa
  const lower = teamName.toLowerCase();
  for (const [key, url] of Object.entries(TEAM_LOGOS)) {
    const keyLower = key.toLowerCase();
    // Match on last word (e.g. "Thunder" in "Oklahoma City Thunder")
    const lastWord = keyLower.split(" ").at(-1)!;
    if (lastWord.length > 4 && lower.includes(lastWord)) return url;
  }
  return null;
}

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
  return market.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function getMarketDetail(market: string, legs: Array<{ line?: number | null }>): string {
  const label = getMarketLabel(market);
  const line  = legs[0]?.line;
  if (line != null && market.includes("spread")) return `${label}  (${line > 0 ? `+${line}` : line})`;
  if (line != null && market.includes("total"))  return `${label}  (O/U ${Math.abs(line)})`;
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

function calcProfitIfWins(legs: Array<{ price: number }>, betSizes: number[], winnerIdx: number): number {
  const decimal   = americanToDecimal(legs[winnerIdx].price);
  const winnerBet = betSizes[winnerIdx] ?? 0;
  const otherBets = betSizes.reduce((s, b, i) => (i !== winnerIdx ? s + b : s), 0);
  return winnerBet * (decimal - 1) - otherBets;
}

// ── Styling ──────────────────────────────────────────────────────────────────

function marginColor(pct: number): string {
  if (pct > 2) return "border-green-500 text-green-500 bg-green-500/10";
  if (pct > 1) return "border-yellow-500 text-yellow-500 bg-yellow-500/10";
  return "border-muted-foreground text-muted-foreground";
}

const BET_COLORS = [
  { badge: "bg-blue-500/15 border-blue-500/50 text-blue-400",   book: "text-blue-400",   input: "bg-blue-500/10 border-blue-500/40 text-blue-200 focus:ring-blue-500",   dot: "bg-blue-500",   strip: "border-l-blue-500"   },
  { badge: "bg-orange-500/15 border-orange-500/50 text-orange-400", book: "text-orange-400", input: "bg-orange-500/10 border-orange-500/40 text-orange-200 focus:ring-orange-500", dot: "bg-orange-500", strip: "border-l-orange-500" },
  { badge: "bg-purple-500/15 border-purple-500/50 text-purple-400", book: "text-purple-400", input: "bg-purple-500/10 border-purple-500/40 text-purple-200 focus:ring-purple-500", dot: "bg-purple-500", strip: "border-l-purple-500" },
];

function betColor(idx: number) { return BET_COLORS[idx % BET_COLORS.length]; }

// ── Reusable logo image with letter fallback ─────────────────────────────────

function LogoImg({ src, alt, size = 24 }: { src: string | null; alt: string; size?: number }) {
  if (!src) return (
    <span
      className="inline-flex items-center justify-center rounded-full bg-secondary text-[10px] font-bold text-muted-foreground shrink-0"
      style={{ width: size, height: size }}
    >
      {alt.slice(0, 2).toUpperCase()}
    </span>
  );
  return (
    <img
      src={src}
      alt={alt}
      width={size}
      height={size}
      className="rounded object-contain shrink-0"
      style={{ width: size, height: size }}
      onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = "none"; }}
    />
  );
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
    if (!isNaN(n) && n > 0) { setBankroll(n); setCustomBets({}); }
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
    return displays.map((v, i) => { const n = parseFloat(v); return isNaN(n) ? (optimal[i] ?? 0) : n; });
  }

  function handleBetInput(eventId: string, legIdx: number, val: string, opp: { legs: Array<{ price: number }> }) {
    setCustomBets((prev) => {
      const current = prev[eventId] ?? getOptimalStrs(opp);
      const updated = [...current]; updated[legIdx] = val;
      return { ...prev, [eventId]: updated };
    });
  }

  if (isLoading && !data) return (
    <div className="space-y-4">
      <Skeleton className="h-8 w-48" />
      <Skeleton className="h-[300px] w-full" />
      <Skeleton className="h-[300px] w-full" />
    </div>
  );

  if (data?.configured === false) return (
    <div className="max-w-2xl mx-auto mt-12">
      <Alert className="border-primary bg-primary/5">
        <KeyRound className="h-5 w-5 text-primary" />
        <AlertTitle className="text-lg font-semibold text-primary">OddsJam API Key Required</AlertTitle>
        <AlertDescription className="mt-2 text-sm leading-relaxed text-muted-foreground">
          Set the <code className="bg-secondary px-1 py-0.5 rounded text-foreground">ODDSJAM_API_KEY</code> environment variable to enable live arbitrage scanning.
        </AlertDescription>
      </Alert>
    </div>
  );

  if (data?.access_denied) return (
    <div className="max-w-2xl mx-auto mt-12">
      <Alert className="border-yellow-500 bg-yellow-500/5">
        <KeyRound className="h-5 w-5 text-yellow-500" />
        <AlertTitle className="text-lg font-semibold text-yellow-600 dark:text-yellow-400">Arbitrage Access Not Included</AlertTitle>
        <AlertDescription className="mt-2 text-sm leading-relaxed text-muted-foreground">
          {data.access_denied_reason || "Your plan does not include arbitrage API access."}{" "}
          Visit <a href="https://oddsjam.com" target="_blank" rel="noopener noreferrer" className="underline text-foreground hover:text-primary">oddsjam.com</a> to upgrade.
        </AlertDescription>
      </Alert>
    </div>
  );

  if (error) return (
    <Alert variant="destructive">
      <AlertCircle className="h-4 w-4" />
      <AlertTitle>Error fetching arbitrage</AlertTitle>
      <AlertDescription>
        The server encountered an error while scanning.
        <Button variant="outline" size="sm" className="ml-4" onClick={() => refetch()}>Retry</Button>
      </AlertDescription>
    </Alert>
  );

  const opps = data?.opportunities ?? [];

  return (
    <div className="space-y-6">
      {/* Header */}
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
            <label className="text-xs text-muted-foreground whitespace-nowrap font-medium">Bankroll $</label>
            <input
              type="number" min="1" step="10" value={bankrollInput}
              onChange={(e) => handleBankrollChange(e.target.value)}
              className="w-24 bg-secondary text-foreground text-sm rounded-md px-2 py-1.5 border border-border outline-none focus:ring-1 focus:ring-primary font-mono"
            />
          </div>
          <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isFetching}>
            <RefreshCw className={`w-3 h-3 mr-1.5 ${isFetching ? "animate-spin" : ""}`} />
            Refresh
          </Button>
          <Badge variant="outline" className="bg-secondary font-mono">{data?.total ?? 0} opportunities</Badge>
        </div>
      </div>

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
            const betSizes     = getParsedBets(opp);
            const displays     = getDisplayValues(opp);
            const totalStaked  = betSizes.reduce((s, b) => s + b, 0);
            const marketDetail = getMarketDetail(opp.market, opp.legs);
            const homeLogo     = getTeamLogo(opp.home_team);
            const awayLogo     = getTeamLogo(opp.away_team);

            return (
              <Card key={i} className="bg-card border-border overflow-hidden flex flex-col">

                {/* ── Game header with team logos ── */}
                <div className="px-4 pt-4 pb-3 border-b border-border">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      {/* Teams with logos */}
                      <div className="flex items-center gap-2 flex-wrap">
                        <div className="flex items-center gap-1.5">
                          <LogoImg src={homeLogo} alt={opp.home_team} size={22} />
                          <span className="font-semibold text-sm leading-tight">{opp.home_team}</span>
                        </div>
                        <span className="text-muted-foreground text-xs font-medium">vs</span>
                        <div className="flex items-center gap-1.5">
                          <LogoImg src={awayLogo} alt={opp.away_team} size={22} />
                          <span className="font-semibold text-sm leading-tight">{opp.away_team}</span>
                        </div>
                      </div>
                      {/* Sport + market */}
                      <div className="flex flex-wrap items-center gap-1.5 mt-1.5">
                        <span className="text-xs uppercase tracking-wider text-muted-foreground font-medium">{opp.sport_key}</span>
                        <span className="text-border text-xs">•</span>
                        <span className="text-xs text-foreground/80 font-semibold">{marketDetail}</span>
                      </div>
                    </div>
                    <Badge variant="outline" className={`font-mono font-bold text-sm shrink-0 ${marginColor(opp.margin_pct)}`}>
                      +{opp.margin_pct.toFixed(2)}%
                    </Badge>
                  </div>

                  {/* Bet position legend */}
                  <div className="flex gap-2 mt-3 flex-wrap">
                    {opp.legs.map((leg, j) => {
                      const c    = betColor(j);
                      const logo = getBookLogo(leg.book);
                      return (
                        <div key={j} className={`flex items-center gap-1.5 px-2 py-1 rounded-full border text-xs font-semibold ${c.badge}`}>
                          <LogoImg src={logo} alt={leg.book} size={14} />
                          Bet {j + 1} → {leg.book}
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* ── Individual bets ── */}
                <CardContent className="p-3 flex-1 space-y-3">
                  {opp.legs.map((leg, j) => {
                    const c      = betColor(j);
                    const profit = calcProfitIfWins(opp.legs, betSizes, j);
                    const logo   = getBookLogo(leg.book);

                    return (
                      <div key={j} className={`rounded-lg border border-border border-l-4 ${c.strip} bg-secondary/20 overflow-hidden`}>

                        {/* Bet # + sportsbook with logo */}
                        <div className="flex items-center justify-between px-3 py-2 bg-secondary/40 border-b border-border">
                          <span className={`text-xs font-bold uppercase tracking-widest ${c.book}`}>
                            BET {j + 1} of {opp.legs.length}
                          </span>
                          <div className={`flex items-center gap-1.5 text-xs font-bold ${c.book}`}>
                            <MapPin className="w-3 h-3" />
                            <LogoImg src={logo} alt={leg.book} size={16} />
                            {leg.book}
                          </div>
                        </div>

                        {/* Selection + odds — line shown ONCE here inside leg.side */}
                        <div className="px-3 py-2">
                          <div className="font-semibold text-sm text-foreground">{leg.side}</div>
                          <div className="text-xs text-muted-foreground mt-0.5">
                            at odds <span className="font-mono font-semibold text-foreground">{formatOdds(leg.price)}</span>
                          </div>
                        </div>

                        {/* Stake + profit */}
                        <div className="px-3 pb-3 flex items-end gap-3">
                          <div className="flex-1">
                            <label className="text-xs text-muted-foreground font-medium mb-1 block">Stake ($)</label>
                            <div className="flex items-center gap-1">
                              <span className="text-xs text-muted-foreground">$</span>
                              <input
                                type="number" min="0" step="1"
                                value={displays[j] ?? ""}
                                onChange={(e) => handleBetInput(opp.event_id, j, e.target.value, opp)}
                                className={`w-full border rounded-md px-2 py-1.5 text-sm outline-none focus:ring-1 font-mono ${c.input}`}
                              />
                            </div>
                          </div>
                          <div className="text-right shrink-0">
                            <div className="text-xs text-muted-foreground mb-1">Profit if wins</div>
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
                      <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">Guaranteed Outcome Summary</span>
                    </div>
                    <div className="space-y-2">
                      {opp.legs.map((leg, j) => {
                        const profit = calcProfitIfWins(opp.legs, betSizes, j);
                        const c      = betColor(j);
                        return (
                          <div key={j} className="flex items-center justify-between text-xs gap-2">
                            <div className="flex items-center gap-2 min-w-0">
                              <span className={`w-2 h-2 rounded-full shrink-0 ${c.dot}`} />
                              {/* Show team/outcome name only — no repeated line */}
                              <span className="text-muted-foreground truncate">
                                If <span className="text-foreground font-semibold">{leg.side}</span> wins
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
