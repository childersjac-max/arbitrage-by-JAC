import { useState, useCallback } from "react";
import { useArbitrageOpportunities, useOpportunitiesSummary } from "@/hooks/use-oddsjam";
import { formatPercent, formatDate } from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Activity, Check, Clock, ExternalLink, Percent, TrendingUp, DollarSign } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";

// ── Sportsbook logos ──────────────────────────────────────────────────────────
const G = "https://www.google.com/s2/favicons?domain=";
const BOOK_LOGOS: Record<string, string> = {
  draftkings: `${G}draftkings.com&sz=64`,
  fanduel:    `${G}fanduel.com&sz=64`,
  betmgm:     `${G}betmgm.com&sz=64`,
  caesars:    `${G}caesars.com&sz=64`,
  bet365:     `${G}bet365.com&sz=64`,
  fanatics:   `${G}fanatics.com&sz=64`,
  thescore:   `${G}thescore.bet&sz=64`,
};

// ── Sportsbook deep links by sport ───────────────────────────────────────────
const BOOK_URLS: Record<string, Record<string, string>> = {
  draftkings: { football:"https://sportsbook.draftkings.com/leagues/football/nfl", basketball:"https://sportsbook.draftkings.com/leagues/basketball/nba", baseball:"https://sportsbook.draftkings.com/leagues/baseball/mlb", hockey:"https://sportsbook.draftkings.com/leagues/hockey/nhl", soccer:"https://sportsbook.draftkings.com/sport/soccer", mma:"https://sportsbook.draftkings.com/sport/mma", default:"https://sportsbook.draftkings.com" },
  fanduel:    { football:"https://sportsbook.fanduel.com/football/nfl", basketball:"https://sportsbook.fanduel.com/basketball/nba", baseball:"https://sportsbook.fanduel.com/baseball/mlb", hockey:"https://sportsbook.fanduel.com/hockey/nhl", soccer:"https://sportsbook.fanduel.com/soccer", mma:"https://sportsbook.fanduel.com/mma", default:"https://sportsbook.fanduel.com" },
  betmgm:     { football:"https://sports.betmgm.com/en/sports/football-11/betting/usa/nfl-35", basketball:"https://sports.betmgm.com/en/sports/basketball-7/betting/usa/nba-6004", baseball:"https://sports.betmgm.com/en/sports/baseball-23/betting/usa/mlb-75", hockey:"https://sports.betmgm.com/en/sports/ice-hockey-19/betting/usa/nhl-41", soccer:"https://sports.betmgm.com/en/sports/soccer-4/betting", default:"https://sports.betmgm.com/en/sports" },
  caesars:    { football:"https://sportsbook.caesars.com/us/nc/bet/sports/american-football", basketball:"https://sportsbook.caesars.com/us/nc/bet/sports/basketball", baseball:"https://sportsbook.caesars.com/us/nc/bet/sports/baseball", hockey:"https://sportsbook.caesars.com/us/nc/bet/sports/ice-hockey", soccer:"https://sportsbook.caesars.com/us/nc/bet/sports/soccer", mma:"https://sportsbook.caesars.com/us/nc/bet/sports/mma", default:"https://sportsbook.caesars.com/us/nc/bet" },
  bet365:     { football:"https://www.bet365.com/#/AS/B4/", basketball:"https://www.bet365.com/#/AS/B6/", baseball:"https://www.bet365.com/#/AS/B18/", hockey:"https://www.bet365.com/#/AS/B17/", soccer:"https://www.bet365.com/#/AS/B1/", tennis:"https://www.bet365.com/#/AS/B13/", default:"https://www.bet365.com" },
  fanatics:   { football:"https://sportsbook.fanatics.com/sports/football/nfl", basketball:"https://sportsbook.fanatics.com/sports/basketball/nba", baseball:"https://sportsbook.fanatics.com/sports/baseball/mlb", hockey:"https://sportsbook.fanatics.com/sports/hockey/nhl", soccer:"https://sportsbook.fanatics.com/sports/soccer", default:"https://sportsbook.fanatics.com" },
  thescore:   { football:"https://www.thescore.bet/sports/american-football/nfl", basketball:"https://www.thescore.bet/sports/basketball/nba", baseball:"https://www.thescore.bet/sports/baseball/mlb", hockey:"https://www.thescore.bet/sports/ice-hockey/nhl", soccer:"https://www.thescore.bet/sports/soccer", default:"https://www.thescore.bet" },
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
  if (!src) return <span className="inline-flex items-center justify-center w-7 h-7 rounded bg-secondary text-[9px] font-bold text-muted-foreground shrink-0">{title.slice(0, 2).toUpperCase()}</span>;
  return <img src={src} alt={title} width={28} height={28} className="rounded object-contain shrink-0" onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = "none"; }} />;
}

// ── Team logos via ESPN CDN (sport-aware to avoid nickname conflicts) ─────────
const ESPN = "https://a.espncdn.com/i/teamlogos";

// nickname/full-name → ESPN abbreviation, keyed by sport
const TEAM_ABBREVS: Record<string, Record<string, string>> = {
  football: {
    // Full names
    "arizona cardinals":"ari","atlanta falcons":"atl","baltimore ravens":"bal","buffalo bills":"buf",
    "carolina panthers":"car","chicago bears":"chi","cincinnati bengals":"cin","cleveland browns":"cle",
    "dallas cowboys":"dal","denver broncos":"den","detroit lions":"det","green bay packers":"gb",
    "houston texans":"hou","indianapolis colts":"ind","jacksonville jaguars":"jax","kansas city chiefs":"kc",
    "las vegas raiders":"lv","los angeles chargers":"lac","los angeles rams":"lar","miami dolphins":"mia",
    "minnesota vikings":"min","new england patriots":"ne","new orleans saints":"no","new york giants":"nyg",
    "new york jets":"nyj","philadelphia eagles":"phi","pittsburgh steelers":"pit","san francisco 49ers":"sf",
    "seattle seahawks":"sea","tampa bay buccaneers":"tb","tennessee titans":"ten","washington commanders":"wsh",
    // Nicknames
    "cardinals":"ari","falcons":"atl","ravens":"bal","bills":"buf","panthers":"car","bears":"chi",
    "bengals":"cin","browns":"cle","cowboys":"dal","broncos":"den","lions":"det","packers":"gb",
    "texans":"hou","colts":"ind","jaguars":"jax","chiefs":"kc","raiders":"lv","chargers":"lac",
    "rams":"lar","dolphins":"mia","vikings":"min","patriots":"ne","saints":"no","giants":"nyg",
    "jets":"nyj","eagles":"phi","steelers":"pit","49ers":"sf","seahawks":"sea","buccaneers":"tb",
    "titans":"ten","commanders":"wsh",
  },
  basketball: {
    "atlanta hawks":"atl","boston celtics":"bos","brooklyn nets":"bkn","charlotte hornets":"cha",
    "chicago bulls":"chi","cleveland cavaliers":"cle","dallas mavericks":"dal","denver nuggets":"den",
    "detroit pistons":"det","golden state warriors":"gs","houston rockets":"hou","indiana pacers":"ind",
    "los angeles clippers":"lac","los angeles lakers":"lal","memphis grizzlies":"mem","miami heat":"mia",
    "milwaukee bucks":"mil","minnesota timberwolves":"min","new orleans pelicans":"nop","new york knicks":"ny",
    "oklahoma city thunder":"okc","orlando magic":"orl","philadelphia 76ers":"phi","phoenix suns":"phx",
    "portland trail blazers":"por","sacramento kings":"sac","san antonio spurs":"sa","toronto raptors":"tor",
    "utah jazz":"utah","washington wizards":"wsh",
    // Nicknames
    "hawks":"atl","celtics":"bos","nets":"bkn","hornets":"cha","bulls":"chi","cavaliers":"cle","cavs":"cle",
    "mavericks":"dal","mavs":"dal","nuggets":"den","pistons":"det","warriors":"gs","rockets":"hou",
    "pacers":"ind","clippers":"lac","lakers":"lal","grizzlies":"mem","heat":"mia","bucks":"mil",
    "timberwolves":"min","wolves":"min","pelicans":"nop","knicks":"ny","thunder":"okc","magic":"orl",
    "76ers":"phi","sixers":"phi","suns":"phx","trail blazers":"por","blazers":"por","kings":"sac",
    "spurs":"sa","raptors":"tor","jazz":"utah","wizards":"wsh",
  },
  baseball: {
    "arizona diamondbacks":"ari","atlanta braves":"atl","baltimore orioles":"bal","boston red sox":"bos",
    "chicago cubs":"chc","chicago white sox":"chw","cincinnati reds":"cin","cleveland guardians":"cle",
    "colorado rockies":"col","detroit tigers":"det","houston astros":"hou","kansas city royals":"kc",
    "los angeles angels":"laa","los angeles dodgers":"lad","miami marlins":"mia","milwaukee brewers":"mil",
    "minnesota twins":"min","new york mets":"nym","new york yankees":"nyy","oakland athletics":"oak",
    "philadelphia phillies":"phi","pittsburgh pirates":"pit","san diego padres":"sd",
    "san francisco giants":"sf","seattle mariners":"sea","st. louis cardinals":"stl",
    "st louis cardinals":"stl","tampa bay rays":"tb","texas rangers":"tex",
    "toronto blue jays":"tor","washington nationals":"wsh",
    // Nicknames
    "diamondbacks":"ari","d-backs":"ari","braves":"atl","orioles":"bal","red sox":"bos","cubs":"chc",
    "white sox":"chw","reds":"cin","guardians":"cle","rockies":"col","tigers":"det","astros":"hou",
    "royals":"kc","angels":"laa","dodgers":"lad","marlins":"mia","brewers":"mil","twins":"min",
    "mets":"nym","yankees":"nyy","athletics":"oak","phillies":"phi","pirates":"pit","padres":"sd",
    "giants":"sf","mariners":"sea","cardinals":"stl","rays":"tb","rangers":"tex","blue jays":"tor",
    "nationals":"wsh",
  },
  hockey: {
    "anaheim ducks":"ana","boston bruins":"bos","buffalo sabres":"buf","calgary flames":"cgy",
    "carolina hurricanes":"car","chicago blackhawks":"chi","colorado avalanche":"col",
    "columbus blue jackets":"cbj","dallas stars":"dal","detroit red wings":"det",
    "edmonton oilers":"edm","florida panthers":"fla","los angeles kings":"lak",
    "minnesota wild":"min","montreal canadiens":"mtl","nashville predators":"nsh",
    "new jersey devils":"njd","new york islanders":"nyi","new york rangers":"nyr",
    "ottawa senators":"ott","philadelphia flyers":"phi","pittsburgh penguins":"pit",
    "san jose sharks":"sjs","seattle kraken":"sea","st. louis blues":"stl","st louis blues":"stl",
    "tampa bay lightning":"tbl","toronto maple leafs":"tor","utah hockey club":"utah",
    "vancouver canucks":"van","vegas golden knights":"vgk","washington capitals":"wsh",
    "winnipeg jets":"wpg",
    // Nicknames
    "ducks":"ana","bruins":"bos","sabres":"buf","flames":"cgy","hurricanes":"car","canes":"car",
    "blackhawks":"chi","hawks":"chi","avalanche":"col","avs":"col","blue jackets":"cbj","stars":"dal",
    "red wings":"det","oilers":"edm","panthers":"fla","kings":"lak","wild":"min",
    "canadiens":"mtl","habs":"mtl","predators":"nsh","preds":"nsh","devils":"njd",
    "islanders":"nyi","rangers":"nyr","senators":"ott","sens":"ott","flyers":"phi","penguins":"pit",
    "pens":"pit","sharks":"sjs","kraken":"sea","blues":"stl","lightning":"tbl","maple leafs":"tor",
    "leafs":"tor","canucks":"van","golden knights":"vgk","capitals":"wsh","caps":"wsh","jets":"wpg",
  },
};

function getTeamLogo(outcome: string, sport: string): string | null {
  if (!outcome) return null;

  // Skip Over/Under and player prop outcomes (no team logo applies)
  const trimmed = outcome.trim();
  if (/^(over|under)(\s|$)/i.test(trimmed)) return null;

  // Strip trailing line/point info: "Chiefs -3.5" → "Chiefs", "Eagles +4.5" → "Eagles"
  const nameOnly = trimmed.replace(/\s*[+-]?\d+\.?\d*\s*$/, "").trim().toLowerCase();

  const sportMap = TEAM_ABBREVS[sport] ?? {};
  // Try exact
  let abbrev = sportMap[nameOnly];
  if (!abbrev) {
    // Try last word (nickname): "kansas city chiefs -3.5" → "chiefs"
    const words = nameOnly.split(/\s+/);
    const last = words[words.length - 1] ?? "";
    abbrev = sportMap[last];
    // Try last two words: "red sox", "blue jays", "trail blazers"
    if (!abbrev && words.length >= 2) {
      abbrev = sportMap[words.slice(-2).join(" ")];
    }
  }
  if (!abbrev) return null;

  const espnSport = sport === "football" ? "nfl"
    : sport === "basketball" ? "nba"
    : sport === "baseball" ? "mlb"
    : sport === "hockey" ? "nhl"
    : null;
  if (!espnSport) return null;

  return `${ESPN}/${espnSport}/500/${abbrev}.png`;
}

// ── Stat label from market key ────────────────────────────────────────────────
function getStatLabel(market: string): string {
  const base = market.includes("::") ? market.split("::")[0]! : market;
  const key = base.replace(/^alternate_/, "").replace(/^player_/, "");
  const LABELS: Record<string, string> = {
    // Basketball
    points: "points", assists: "assists", rebounds: "rebounds",
    steals: "steals", blocks: "blocks", threes: "3-pointers",
    pts_rebs_asts: "PRA", pts_rebs: "Pts+Reb", pts_asts: "Pts+Ast",
    rebs_asts: "Reb+Ast", double_double: "double-double",
    // Baseball
    hits: "hits", home_runs: "home runs", strikeouts: "strikeouts",
    total_bases: "total bases", rbi: "RBIs", walks: "walks",
    runs_scored: "runs", hits_runs_rbis: "H+R+RBI",
    // Football
    passing_yards: "pass yds", rushing_yards: "rush yds",
    receiving_yards: "rec yds", receptions: "receptions",
    touchdowns: "TDs", interceptions: "INTs",
    passing_tds: "pass TDs", rushing_tds: "rush TDs", receiving_tds: "rec TDs",
    kicking_points: "kicking pts", tackles: "tackles",
    // Hockey
    shots_on_goal: "shots", goals: "goals",
    // Generic
    fantasy_points: "fantasy pts",
  };
  return LABELS[key] ?? key.replace(/_/g, " ");
}

// Format a player-prop outcome: show stat line number and label
// "Luke Kornet Over +3.5" + player_rebounds → "Luke Kornet Over 3.5 rebounds"
function formatOutcome(outcome: string, market: string): string {
  const isPlayerProp = /player/i.test(market);
  if (!isPlayerProp) return outcome;
  const stat = getStatLabel(market);
  // Extract the trailing number from canonical form (e.g. "+3.5" or "3.5")
  const m = outcome.match(/^(.*?)\s+([+-]?\d+\.?\d*)\s*$/);
  if (m) {
    const base = m[1]!;
    const num = parseFloat(m[2]!);
    return `${base} ${num} ${stat}`;
  }
  return `${outcome} ${stat}`;
}

// ── Bet type helpers ──────────────────────────────────────────────────────────
function getBetType(market: string): string {
  const base = market.includes("::") ? market.split("::")[0]! : market;
  if (base.startsWith("alternate_player_")) return "Alt Prop";
  if (base.startsWith("player_"))           return "Player Prop";
  if (base === "alternate_spread" || base === "alternate_point_spread") return "Alt Spread";
  if (base === "alternate_total" || base.startsWith("alternate_total_")) return "Alt Total";
  if (base === "moneyline" || base === "moneyline_3-way") return "Moneyline";
  if (base === "point_spread") return "Spread";
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
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [bankroll, setBankroll] = useState<number>(100);

  const copyBet = useCallback((key: string, text: string, url: string) => {
    navigator.clipboard.writeText(text).catch(() => {});
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
    const a = Object.assign(document.createElement("a"), {
      href: url, target: "_blank", rel: "noopener noreferrer",
    });
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  }, []);

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
            <CardTitle className="text-sm font-medium">Bankroll</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-1">
              <span className="text-xl font-bold text-muted-foreground">$</span>
              <Input
                type="number"
                min={1}
                step={10}
                value={bankroll}
                onChange={(e) => setBankroll(Math.max(1, Number(e.target.value) || 1))}
                className="text-2xl font-bold font-mono h-9 px-2 border-0 shadow-none focus-visible:ring-0 p-0 w-full"
              />
            </div>
            <p className="text-xs text-muted-foreground mt-1">Total to spread across both sides</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-7">
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
              <div className="space-y-2">{[...Array(5)].map((_, i) => <Skeleton key={i} className="h-16 w-full" />)}</div>
            ) : opportunities?.length === 0 ? (
              <div className="text-center py-10 text-muted-foreground border border-dashed border-border rounded-md">
                No arbitrage opportunities found. Markets might be tight right now.
              </div>
            ) : (
              <Accordion type="single" collapsible className="w-full space-y-2">
                {opportunities?.map((opp) => {
                  const betType = getBetType(opp.market);
                  const homeLogoUrl = getTeamLogo(opp.homeTeam, opp.sport);
                  const awayLogoUrl = getTeamLogo(opp.awayTeam, opp.sport);
                  const scale = bankroll / 100;
                  const totalStake = opp.legs.reduce((s, l) => s + l.stake, 0) * scale;
                  const guaranteedReturn = (opp.legs[0]
                    ? opp.legs[0].stake * (opp.legs[0].price > 0
                        ? (opp.legs[0].price / 100 + 1)
                        : (100 / Math.abs(opp.legs[0].price) + 1))
                    : (totalStake / scale) * (1 + opp.profitPercent / 100)) * scale;

                  return (
                    <AccordionItem key={opp.id} value={opp.id}
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
                            <div className="flex items-center gap-2">
                              {homeLogoUrl && <img src={homeLogoUrl} alt={opp.homeTeam} width={24} height={24} className="object-contain shrink-0" onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = "none"; }} />}
                              {awayLogoUrl && <img src={awayLogoUrl} alt={opp.awayTeam} width={24} height={24} className="object-contain shrink-0" onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = "none"; }} />}
                              <span className="font-semibold text-left">{opp.homeTeam} vs {opp.awayTeam}</span>
                            </div>
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
                          {opp.legs.map((leg, i) => {
                            const teamLogo = getTeamLogo(leg.outcome, opp.sport);
                            const legKey = `${opp.id}-${i}`;
                            const isCopied = copiedKey === legKey;
                            const bookUrl = getBookUrl(leg.bookmakerTitle, opp.sport);
                            const oddsStr = leg.price > 0 ? `+${leg.price}` : `${leg.price}`;
                            const clipText = [
                              `${leg.bookmakerTitle}: ${formatOutcome(leg.outcome, opp.market)} @ ${oddsStr}`,
                              `Stake: $${(leg.stake * scale).toFixed(2)}`,
                              `Game: ${opp.homeTeam} vs ${opp.awayTeam}`,
                              `Market: ${cleanMarketLabel(opp.market)}`,
                            ].join("\n");
                            return (
                              <div key={i}
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
                                    <button
                                      onClick={(e) => { e.stopPropagation(); copyBet(legKey, clipText, bookUrl); }}
                                      className="inline-flex items-center gap-1 text-xs font-bold mt-0.5 transition-colors"
                                      style={{ color: isCopied ? "var(--color-success, #22c55e)" : "var(--color-primary)" }}
                                    >
                                      {isCopied
                                        ? <><Check className="w-3 h-3" /> Copied!</>
                                        : <><ExternalLink className="w-3 h-3" /> Open & Bet</>}
                                    </button>
                                  </div>
                                </div>

                                <div className="hidden sm:block w-px h-10 bg-border shrink-0" />

                                {/* Bet details */}
                                <div className="flex-1 flex flex-col gap-1">
                                  {/* Team logo + outcome name */}
                                  <div className="flex items-center gap-2">
                                    {teamLogo && (
                                      <img
                                        src={teamLogo}
                                        alt={leg.outcome}
                                        width={32}
                                        height={32}
                                        className="object-contain rounded"
                                        onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = "none"; }}
                                      />
                                    )}
                                    <div className="flex items-center gap-2 flex-wrap">
                                      <Badge variant="outline" className={`text-xs ${betTypeColor(betType)}`}>{betType}</Badge>
                                      <span className="font-bold text-sm">{formatOutcome(leg.outcome, opp.market)}</span>
                                    </div>
                                  </div>
                                  <p className="text-xs text-muted-foreground">
                                    Bet{" "}
                                    <span className="font-mono font-semibold text-foreground">${(leg.stake * scale).toFixed(2)}</span>
                                    {" "}at odds{" "}
                                    <span className={`font-mono font-bold text-base ${leg.price > 0 ? "text-success" : "text-foreground"}`}>
                                      {formatOdds(leg.price)}
                                    </span>
                                  </p>
                                </div>

                                {/* Stake chip */}
                                <div className="flex flex-col items-end sm:items-center shrink-0">
                                  <span className="text-xs text-muted-foreground">Stake</span>
                                  <span className="font-mono font-bold text-lg text-success">${(leg.stake * scale).toFixed(2)}</span>
                                </div>
                              </div>
                            );
                          })}

                          <div className="flex items-center justify-between px-1 pt-1 text-xs text-muted-foreground">
                            <span>Detected: {formatDate(opp.detectedAt)}</span>
                            <span className="font-mono">
                              Total bet: <span className="text-foreground font-semibold">${totalStake.toFixed(2)}</span>
                              &nbsp;·&nbsp;
                              Implied: <span className="text-foreground font-semibold">{(opp.totalImpliedProbability * 100).toFixed(2)}%</span>
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

        <div className="col-span-7 lg:col-span-2 space-y-4">
          <Card>
            <CardHeader><CardTitle className="text-sm">Sport Breakdown</CardTitle></CardHeader>
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
                  {(!summary?.sportBreakdown || summary.sportBreakdown.length === 0) && <div className="text-sm text-muted-foreground">No data available</div>}
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle className="text-sm">Market Breakdown</CardTitle></CardHeader>
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
                  {(!summary?.marketBreakdown || summary.marketBreakdown.length === 0) && <div className="text-sm text-muted-foreground">No data available</div>}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
