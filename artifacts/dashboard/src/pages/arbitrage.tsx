import { useState, useEffect, useRef, useCallback } from "react";
import {
  useGetArbitrageOpportunities,
  getGetArbitrageOpportunitiesQueryKey,
} from "@workspace/api-client-react";
import { formatMoney, formatTimeAgo } from "@/lib/format";
import { useSelectedDate, isSameDay } from "@/lib/date-context";
import { Card, CardContent } from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { KeyRound, RefreshCw, Info, AlertCircle, Bell, BellOff, ExternalLink, Check } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

function marginColor(pct: number) {
  if (pct > 2) return "border-green-500 text-green-500 bg-green-500/10";
  if (pct > 1) return "border-yellow-500 text-yellow-500 bg-yellow-500/10";
  return "border-muted-foreground text-muted-foreground";
}

const BOOK_URLS = {
  draftkings: { football:"https://sportsbook.draftkings.com/leagues/football/nfl", basketball:"https://sportsbook.draftkings.com/leagues/basketball/nba", baseball:"https://sportsbook.draftkings.com/leagues/baseball/mlb", hockey:"https://sportsbook.draftkings.com/leagues/hockey/nhl", soccer:"https://sportsbook.draftkings.com/sport/soccer", mma:"https://sportsbook.draftkings.com/sport/mma", default:"https://sportsbook.draftkings.com" },
  fanduel:    { football:"https://sportsbook.fanduel.com/football/nfl", basketball:"https://sportsbook.fanduel.com/basketball/nba", baseball:"https://sportsbook.fanduel.com/baseball/mlb", hockey:"https://sportsbook.fanduel.com/hockey/nhl", soccer:"https://sportsbook.fanduel.com/soccer", mma:"https://sportsbook.fanduel.com/mma", default:"https://sportsbook.fanduel.com" },
  betmgm:     { football:"https://sports.betmgm.com/en/sports/football-11/betting/usa/nfl-35", basketball:"https://sports.betmgm.com/en/sports/basketball-7/betting/usa/nba-6004", baseball:"https://sports.betmgm.com/en/sports/baseball-23/betting/usa/mlb-75", hockey:"https://sports.betmgm.com/en/sports/ice-hockey-19/betting/usa/nhl-41", soccer:"https://sports.betmgm.com/en/sports/soccer-4/betting", default:"https://sports.betmgm.com/en/sports" },
  caesars:    { football:"https://sportsbook.caesars.com/us/nc/bet/sports/american-football", basketball:"https://sportsbook.caesars.com/us/nc/bet/sports/basketball", baseball:"https://sportsbook.caesars.com/us/nc/bet/sports/baseball", hockey:"https://sportsbook.caesars.com/us/nc/bet/sports/ice-hockey", soccer:"https://sportsbook.caesars.com/us/nc/bet/sports/soccer", mma:"https://sportsbook.caesars.com/us/nc/bet/sports/mma", default:"https://sportsbook.caesars.com/us/nc/bet" },
  bet365:     { football:"https://www.bet365.com/#/AS/B4/", basketball:"https://www.bet365.com/#/AS/B6/", baseball:"https://www.bet365.com/#/AS/B18/", hockey:"https://www.bet365.com/#/AS/B17/", soccer:"https://www.bet365.com/#/AS/B1/", tennis:"https://www.bet365.com/#/AS/B13/", default:"https://www.bet365.com" },
  fanatics:   { football:"https://sportsbook.fanatics.com/sports/football", basketball:"https://sportsbook.fanatics.com/sports/basketball", baseball:"https://sportsbook.fanatics.com/sports/baseball", hockey:"https://sportsbook.fanatics.com/sports/hockey", soccer:"https://sportsbook.fanatics.com/sports/soccer", default:"https://sportsbook.fanatics.com" },
  thescore:   { football:"https://www.thescore.bet/sports/american-football", basketball:"https://www.thescore.bet/sports/basketball", baseball:"https://www.thescore.bet/sports/baseball", hockey:"https://www.thescore.bet/sports/ice-hockey", soccer:"https://www.thescore.bet/sports/soccer", default:"https://www.thescore.bet" },
};

function getBookUrl(bookName: string, sportKey: string) {
  const key = (bookName || "").toLowerCase().replace(/\s+/g, "_").replace(/[^a-z0-9_]/g, "");
  const urls = (BOOK_URLS as Record<string, Record<string, string>>)[key];
  if (!urls) return "#";
  const sport = (sportKey || "").includes("football") ? "football"
    : (sportKey || "").includes("basketball") ? "basketball"
    : (sportKey || "").includes("baseball") ? "baseball"
    : (sportKey || "").includes("hockey") ? "hockey"
    : (sportKey || "").includes("soccer") ? "soccer"
    : (sportKey || "").includes("tennis") ? "tennis"
    : (sportKey || "").includes("mma") ? "mma"
    : "default";
  return urls[sport] ?? urls["default"] ?? "#";
}

function getBetType(market: string) {
  if (!market) return "";
  const m = market.toLowerCase();
  if (m.includes("alternate") && m.includes("player")) return "Alt Prop";
  if (m.includes("player")) return "Player Prop";
  if (m.includes("alternate") && (m.includes("spread") || m.includes("point_spread"))) return "Alt Spread";
  if (m.includes("alternate") && m.includes("total")) return "Alt Total";
  if (m === "h2h" || m.includes("moneyline") || m.includes("h2h")) return "Moneyline";
  if (m.includes("spread") || m.includes("point_spread")) return "Spread";
  if (m.includes("total")) return "Total";
  return market.replace(/_/g, " ").replace(/\b\w/g, (ch) => ch.toUpperCase());
}

function betTypeBadgeClass(type: string) {
  if (type === "Moneyline") return "border-blue-500/50 text-blue-400 bg-blue-500/10";
  if (type === "Spread" || type === "Alt Spread") return "border-purple-500/50 text-purple-400 bg-purple-500/10";
  if (type === "Total" || type === "Alt Total") return "border-orange-500/50 text-orange-400 bg-orange-500/10";
  if (type === "Player Prop" || type === "Alt Prop") return "border-pink-500/50 text-pink-400 bg-pink-500/10";
  return "border-muted-foreground/50 text-muted-foreground";
}

function getStatLabel(market: string): string {
  const base = market.includes("::") ? market.split("::")[0]! : market;
  const key = base.replace(/^alternate_/, "").replace(/^player_/, "");
  const LABELS: Record<string, string> = {
    points:"points", assists:"assists", rebounds:"rebounds", steals:"steals", blocks:"blocks",
    threes:"3-pointers", pts_rebs_asts:"PRA", pts_rebs:"Pts+Reb", pts_asts:"Pts+Ast", rebs_asts:"Reb+Ast",
    hits:"hits", home_runs:"home runs", strikeouts:"strikeouts", total_bases:"total bases",
    rbi:"RBIs", walks:"walks", runs_scored:"runs", hits_runs_rbis:"H+R+RBI",
    passing_yards:"pass yds", rushing_yards:"rush yds", receiving_yards:"rec yds",
    receptions:"receptions", touchdowns:"TDs", interceptions:"INTs",
    passing_tds:"pass TDs", rushing_tds:"rush TDs", receiving_tds:"rec TDs",
    kicking_points:"kicking pts", tackles:"tackles", shots_on_goal:"shots", goals:"goals",
    fantasy_points:"fantasy pts",
  };
  return LABELS[key] ?? key.replace(/_/g, " ");
}

function formatSide(side: string | undefined, line: number | null | undefined, market: string): string {
  if (!side) return "";
  const isPlayerProp = /player/i.test(market);
  if (isPlayerProp) {
    const cleaned = side.replace(/\s+[+-]\d+\.?\d*\s*$/, "").trim();
    return `${cleaned} ${getStatLabel(market)}`;
  }
  if (line != null) return `${side} ${line > 0 ? `+${line}` : line}`;
  return side;
}

const ESPN = "https://a.espncdn.com/i/teamlogos";
const TEAM_ABBREVS: Record<string, Record<string, string>> = {
  football: { "arizona cardinals":"ari","atlanta falcons":"atl","baltimore ravens":"bal","buffalo bills":"buf","carolina panthers":"car","chicago bears":"chi","cincinnati bengals":"cin","cleveland browns":"cle","dallas cowboys":"dal","denver broncos":"den","detroit lions":"det","green bay packers":"gb","houston texans":"hou","indianapolis colts":"ind","jacksonville jaguars":"jax","kansas city chiefs":"kc","las vegas raiders":"lv","los angeles chargers":"lac","los angeles rams":"lar","miami dolphins":"mia","minnesota vikings":"min","new england patriots":"ne","new orleans saints":"no","new york giants":"nyg","new york jets":"nyj","philadelphia eagles":"phi","pittsburgh steelers":"pit","san francisco 49ers":"sf","seattle seahawks":"sea","tampa bay buccaneers":"tb","tennessee titans":"ten","washington commanders":"wsh","cardinals":"ari","falcons":"atl","ravens":"bal","bills":"buf","panthers":"car","bears":"chi","bengals":"cin","browns":"cle","cowboys":"dal","broncos":"den","lions":"det","packers":"gb","texans":"hou","colts":"ind","jaguars":"jax","chiefs":"kc","raiders":"lv","chargers":"lac","rams":"lar","dolphins":"mia","vikings":"min","patriots":"ne","saints":"no","giants":"nyg","jets":"nyj","eagles":"phi","steelers":"pit","49ers":"sf","seahawks":"sea","buccaneers":"tb","titans":"ten","commanders":"wsh" },
  basketball: { "atlanta hawks":"atl","boston celtics":"bos","brooklyn nets":"bkn","charlotte hornets":"cha","chicago bulls":"chi","cleveland cavaliers":"cle","dallas mavericks":"dal","denver nuggets":"den","detroit pistons":"det","golden state warriors":"gs","houston rockets":"hou","indiana pacers":"ind","los angeles clippers":"lac","los angeles lakers":"lal","memphis grizzlies":"mem","miami heat":"mia","milwaukee bucks":"mil","minnesota timberwolves":"min","new orleans pelicans":"nop","new york knicks":"ny","oklahoma city thunder":"okc","orlando magic":"orl","philadelphia 76ers":"phi","phoenix suns":"phx","portland trail blazers":"por","sacramento kings":"sac","san antonio spurs":"sa","toronto raptors":"tor","utah jazz":"utah","washington wizards":"wsh","hawks":"atl","celtics":"bos","nets":"bkn","hornets":"cha","bulls":"chi","cavaliers":"cle","cavs":"cle","mavericks":"dal","mavs":"dal","nuggets":"den","pistons":"det","warriors":"gs","rockets":"hou","pacers":"ind","clippers":"lac","lakers":"lal","grizzlies":"mem","heat":"mia","bucks":"mil","timberwolves":"min","wolves":"min","pelicans":"nop","knicks":"ny","thunder":"okc","magic":"orl","76ers":"phi","sixers":"phi","suns":"phx","trail blazers":"por","blazers":"por","kings":"sac","spurs":"sa","raptors":"tor","jazz":"utah","wizards":"wsh" },
  baseball: { "arizona diamondbacks":"ari","atlanta braves":"atl","baltimore orioles":"bal","boston red sox":"bos","chicago cubs":"chc","chicago white sox":"chw","cincinnati reds":"cin","cleveland guardians":"cle","colorado rockies":"col","detroit tigers":"det","houston astros":"hou","kansas city royals":"kc","los angeles angels":"laa","los angeles dodgers":"lad","miami marlins":"mia","milwaukee brewers":"mil","minnesota twins":"min","new york mets":"nym","new york yankees":"nyy","oakland athletics":"oak","philadelphia phillies":"phi","pittsburgh pirates":"pit","san diego padres":"sd","san francisco giants":"sf","seattle mariners":"sea","st. louis cardinals":"stl","st louis cardinals":"stl","tampa bay rays":"tb","texas rangers":"tex","toronto blue jays":"tor","washington nationals":"wsh","diamondbacks":"ari","d-backs":"ari","braves":"atl","orioles":"bal","red sox":"bos","cubs":"chc","white sox":"chw","reds":"cin","guardians":"cle","rockies":"col","tigers":"det","astros":"hou","royals":"kc","angels":"laa","dodgers":"lad","marlins":"mia","brewers":"mil","twins":"min","mets":"nym","yankees":"nyy","athletics":"oak","phillies":"phi","pirates":"pit","padres":"sd","giants":"sf","mariners":"sea","cardinals":"stl","rays":"tb","rangers":"tex","blue jays":"tor","nationals":"wsh" },
  hockey: { "anaheim ducks":"ana","boston bruins":"bos","buffalo sabres":"buf","calgary flames":"cgy","carolina hurricanes":"car","chicago blackhawks":"chi","colorado avalanche":"col","columbus blue jackets":"cbj","dallas stars":"dal","detroit red wings":"det","edmonton oilers":"edm","florida panthers":"fla","los angeles kings":"lak","minnesota wild":"min","montreal canadiens":"mtl","nashville predators":"nsh","new jersey devils":"njd","new york islanders":"nyi","new york rangers":"nyr","ottawa senators":"ott","philadelphia flyers":"phi","pittsburgh penguins":"pit","san jose sharks":"sjs","seattle kraken":"sea","st. louis blues":"stl","st louis blues":"stl","tampa bay lightning":"tbl","toronto maple leafs":"tor","utah hockey club":"utah","vancouver canucks":"van","vegas golden knights":"vgk","washington capitals":"wsh","winnipeg jets":"wpg","ducks":"ana","bruins":"bos","sabres":"buf","flames":"cgy","hurricanes":"car","canes":"car","blackhawks":"chi","avalanche":"col","avs":"col","blue jackets":"cbj","stars":"dal","red wings":"det","oilers":"edm","panthers":"fla","kings":"lak","wild":"min","canadiens":"mtl","habs":"mtl","predators":"nsh","preds":"nsh","devils":"njd","islanders":"nyi","rangers":"nyr","senators":"ott","sens":"ott","flyers":"phi","penguins":"pit","pens":"pit","sharks":"sjs","kraken":"sea","blues":"stl","lightning":"tbl","maple leafs":"tor","leafs":"tor","canucks":"van","golden knights":"vgk","capitals":"wsh","caps":"wsh","jets":"wpg" },
};

function getTeamLogo(side: string | undefined, sportKey: string | undefined): string | null {
  if (!side || !sportKey) return null;
  const trimmed = side.trim();
  if (/^(over|under)(\s|$)/i.test(trimmed)) return null;
  const nameOnly = trimmed.replace(/\s*[+-]?\d+\.?\d*\s*$/, "").trim().toLowerCase();
  const sport = sportKey.includes("football") ? "football" : sportKey.includes("basketball") ? "basketball"
    : sportKey.includes("baseball") ? "baseball" : sportKey.includes("hockey") ? "hockey" : null;
  if (!sport) return null;
  const sportMap = TEAM_ABBREVS[sport] ?? {};
  let abbrev = sportMap[nameOnly];
  if (!abbrev) {
    const words = nameOnly.split(/\s+/);
    abbrev = sportMap[words[words.length - 1] ?? ""];
    if (!abbrev && words.length >= 2) abbrev = sportMap[words.slice(-2).join(" ")];
  }
  if (!abbrev) return null;
  const league = sport === "football" ? "nfl" : sport === "basketball" ? "nba"
    : sport === "baseball" ? "mlb" : sport === "hockey" ? "nhl" : null;
  if (!league) return null;
  return `${ESPN}/${league}/500/${abbrev}.png`;
}

function calcStakes(price: number, bankroll: number, oppPrice: number): number {
  const toImplied = (p: number) => p > 0 ? 100 / (p + 100) : -p / (-p + 100);
  const imp1 = toImplied(price);
  const imp2 = toImplied(oppPrice);
  const total = imp1 + imp2;
  if (total <= 0) return bankroll / 2;
  return Math.round((imp1 / total) * bankroll * 100) / 100;
}

function useArbNotifications(
  opportunities: Array<{ event_id?: string; market?: string; margin_pct: number; home_team?: string; away_team?: string }> | undefined,
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
    opportunities.filter((o) => o.margin_pct > 1).forEach((opp) => {
      const key = `${opp.event_id ?? ""}-${opp.market ?? ""}-${opp.margin_pct.toFixed(2)}`;
      if (!notifiedRef.current.has(key)) {
        notifiedRef.current.add(key);
        new Notification(`ARB +${opp.margin_pct.toFixed(2)}% — ${opp.home_team ?? ""} vs ${opp.away_team ?? ""}`, {
          body: `Market: ${opp.market ?? ""}. Open the app to view stakes.`,
          icon: "/favicon.ico",
        });
      }
    });
  }, [opportunities, notifEnabled]);
  return { notifEnabled, requestPermission };
}

export default function Arbitrage() {
  const [bankroll, setBankroll] = useState<number>(100);
  const [bankrollInput, setBankrollInput] = useState<string>("100");
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const { selectedDate } = useSelectedDate();

  const copyBet = useCallback((key: string, text: string, url: string) => {
    navigator.clipboard.writeText(text).catch(() => {});
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
    window.open(url, "_blank", "noopener,noreferrer");
  }, []);

  const { data, isLoading, error, refetch, isFetching } = useGetArbitrageOpportunities(
    undefined,
    { query: { queryKey: getGetArbitrageOpportunitiesQueryKey(), refetchInterval: 30000 } },
  );

  const allOpps = (data?.opportunities ?? []).slice().sort((a, b) => b.margin_pct - a.margin_pct);
  const filteredOpps = allOpps.filter((opp) => {
    if (!opp.commence_time) return true;
    return isSameDay(new Date(opp.commence_time), selectedDate);
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
          <AlertTitle className="text-lg font-semibold text-primary">OddsJam API Key Required</AlertTitle>
          <AlertDescription className="mt-2 text-sm leading-relaxed text-muted-foreground">
            Live arbitrage scanning requires an active OddsJam API key. Set the{" "}
            <code className="bg-secondary px-1 py-0.5 rounded text-foreground">ODDSJAM_API_KEY</code>{" "}
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
          <AlertTitle className="text-lg font-semibold text-yellow-600 dark:text-yellow-400">Arbitrage Access Not Included</AlertTitle>
          <AlertDescription className="mt-2 text-sm leading-relaxed text-muted-foreground">
            {data.access_denied_reason || "Your OddsJam plan does not include arbitrage API access."}{" "}
            Visit <a href="https://oddsjam.com" target="_blank" rel="noopener noreferrer" className="underline text-foreground hover:text-primary">oddsjam.com</a>{" "}
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
          The server encountered an error.{" "}
          <Button variant="outline" size="sm" className="ml-4" onClick={() => refetch()}>Retry</Button>
        </AlertDescription>
      </Alert>
    );
  }

  const dateLabel = selectedDate.toLocaleDateString("en-US", { weekday: "long", month: "short", day: "numeric" });

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
          <button onClick={requestPermission} title={notifEnabled ? "Notifications on" : "Enable arb alerts"}
            className={`p-1.5 rounded transition-colors ${notifEnabled ? "text-green-500 hover:bg-green-500/10" : "text-muted-foreground hover:bg-secondary"}`}>
            {notifEnabled ? <Bell className="w-4 h-4" /> : <BellOff className="w-4 h-4" />}
          </button>
          <div className="flex items-center gap-2">
            <label className="text-xs text-muted-foreground whitespace-nowrap font-medium">Bankroll $</label>
            <input type="number" min="100" step="100" value={bankrollInput}
              onChange={(e) => handleBankrollChange(e.target.value)}
              className="w-24 bg-secondary text-foreground text-sm rounded-md px-2 py-1.5 border border-border outline-none focus:ring-1 focus:ring-primary font-mono" />
          </div>
          <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isFetching}>
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
            const stakes = opp.legs.length === 2
              ? [calcStakes(prices[0], bankroll, prices[1]), calcStakes(prices[1], bankroll, prices[0])]
              : opp.legs.map((l) => l.stake ?? null);
            const bt = getBetType(opp.market ?? "");

            return (
              <Card key={i} className="bg-card border-border overflow-hidden flex flex-col">
                <div className="p-4 border-b border-border bg-secondary/20 flex items-start justify-between">
                  <div>
                    {(() => { const hl = getTeamLogo(opp.home_team, opp.sport_key); const al = getTeamLogo(opp.away_team, opp.sport_key); return (<div className="flex items-center gap-2"><>{hl && <img src={hl} alt={opp.home_team ?? ""} width={24} height={24} className="object-contain shrink-0" onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = "none"; }} />}</>{al && <img src={al} alt={opp.away_team ?? ""} width={24} height={24} className="object-contain shrink-0" onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = "none"; }} />}<span className="font-semibold">{opp.home_team} vs {opp.away_team}</span></div>); })()}
                    <div className="text-xs text-muted-foreground flex items-center gap-2 mt-1">
                      <span className="uppercase tracking-wider">{opp.sport_key}</span>
                      <span>•</span>
                      <span className={`inline-flex items-center rounded border px-1.5 py-0.5 text-xs font-semibold ${betTypeBadgeClass(bt)}`}>{bt || opp.market}</span>
                      {opp.commence_time && (
                        <><span>•</span><span>{new Date(opp.commence_time).toLocaleTimeString("en-US", { hour:"numeric", minute:"2-digit" })}</span></>
                      )}
                    </div>
                  </div>
                  <Badge variant="outline" className={`font-mono font-bold text-sm ml-2 shrink-0 ${marginColor(opp.margin_pct)}`}>
                    +{opp.margin_pct.toFixed(2)}%
                  </Badge>
                </div>

                <div className="flex flex-col divide-y divide-border">
                  {opp.legs.map((leg, j) => {
                    const teamLogo = getTeamLogo(leg.side, opp.sport_key);
                    const displaySide = formatSide(leg.side, leg.line, opp.market ?? "");
                    const legKey = `${i}-${j}`;
                    const isCopied = copiedKey === legKey;
                    const bookUrl = getBookUrl(leg.book ?? "", opp.sport_key ?? "");
                    const oddsStr = leg.price > 0 ? `+${leg.price}` : `${leg.price}`;
                    const stakeAmt = stakes[j];
                    const clipText = [
                      `${leg.book}: ${displaySide}`,
                      `Odds: ${oddsStr}${stakeAmt != null ? `  |  Stake: ${formatMoney(stakeAmt)}` : ""}`,
                      `Game: ${opp.home_team} vs ${opp.away_team}`,
                    ].join("\n");

                    return (
                      <div key={j} className="flex items-center gap-3 px-4 py-3 hover:bg-secondary/10">
                        <div className="flex items-center justify-center w-7 h-7 rounded-full bg-primary/10 text-primary font-bold text-xs shrink-0">
                          {j + 1}
                        </div>
                        {teamLogo ? (
                          <img src={teamLogo} alt={leg.side ?? ""} width={32} height={32}
                            className="object-contain rounded shrink-0"
                            onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = "none"; }} />
                        ) : <div className="w-8 shrink-0" />}
                        <div className="flex-1 min-w-0">
                          <div className="font-semibold text-sm">{displaySide}</div>
                          <div className="flex items-center gap-1.5 mt-0.5">
                            <span className="text-xs text-muted-foreground font-medium">{leg.book}</span>
                            <span className="text-muted-foreground/40">·</span>
                            <button
                              onClick={() => copyBet(legKey, clipText, bookUrl)}
                              className={`inline-flex items-center gap-0.5 text-xs font-bold transition-colors ${isCopied ? "text-green-500" : "text-primary hover:underline"}`}
                            >
                              {isCopied
                                ? <><Check className="w-2.5 h-2.5" /> Copied!</>
                                : <><ExternalLink className="w-2.5 h-2.5" /> Bet Now</>}
                            </button>
                          </div>
                        </div>
                        <div className="flex flex-col items-end shrink-0">
                          <div className={`font-mono font-bold text-base ${leg.price > 0 ? "text-green-500" : ""}`}>
                            {oddsStr}
                          </div>
                          {stakeAmt != null && (
                            <div className="font-mono text-primary bg-primary/10 px-2 py-0.5 rounded text-xs font-semibold mt-0.5">
                              {formatMoney(stakeAmt)}
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
