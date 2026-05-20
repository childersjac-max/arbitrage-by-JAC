import type { HistoryRecord } from "./opportunity-history";

export const SPORT_FILTERS = [
  { value: "all", label: "All Sports" },
  { value: "baseball", label: "Baseball" },
  { value: "basketball", label: "Basketball" },
  { value: "wnba", label: "WNBA" },
  { value: "football", label: "Football" },
  { value: "golf", label: "Golf" },
  { value: "hockey", label: "Hockey" },
  { value: "soccer", label: "Soccer" },
] as const;

export const LEAGUE_FILTERS = [
  { value: "all", label: "All Leagues" },
  { value: "wnba", label: "WNBA" },
  { value: "pga", label: "PGA Tour" },
  { value: "mls", label: "MLS" },
  { value: "epl", label: "EPL" },
  { value: "ucl", label: "Champions League" },
] as const;

function hourLabel12(h: number): string {
  if (h === 0) return "12 AM";
  if (h === 12) return "12 PM";
  return h < 12 ? `${h} AM` : `${h - 12} PM`;
}

function startOfLocalDay(d: Date): Date {
  const x = new Date(d);
  x.setHours(0, 0, 0, 0);
  return x;
}

function rangeWindow(range: string) {
  const now = new Date();
  if (range === "today") {
    return {
      since: startOfLocalDay(now),
      until: new Date(startOfLocalDay(now).getTime() + 86400000 - 1),
      bucketUnit: "hour" as const,
      pad24Hours: true,
    };
  }
  if (range === "30d") {
    return {
      since: new Date(now.getTime() - 30 * 86400000),
      until: now,
      bucketUnit: "day" as const,
      pad24Hours: false,
    };
  }
  return {
    since: new Date(now.getTime() - 7 * 86400000),
    until: now,
    bucketUnit: "day" as const,
    pad24Hours: false,
  };
}

function matchesSport(opp: HistoryRecord, sport: string): boolean {
  if (!sport || sport === "all") return true;
  const S = sport.toLowerCase();
  const s = (opp.sport || "").toLowerCase();
  const lg = (opp.league || "").toLowerCase();
  if (S === "wnba") return lg === "wnba" || s === "wnba";
  if (S === "pga" || S === "golf") return s === "golf" || lg === "pga";
  return s === S;
}

function matchesLeague(opp: HistoryRecord, league: string): boolean {
  if (!league || league === "all") return true;
  const L = league.toLowerCase();
  const sport = (opp.sport || "").toLowerCase();
  const lg = (opp.league || "").toLowerCase();
  if (L === "soccer") return sport === "soccer";
  if (L === "wnba") return lg === "wnba";
  if (L === "pga") return sport === "golf" || lg === "pga";
  if (L === "mls") return lg === "mls";
  if (L === "epl") return lg === "epl";
  if (L === "ucl") return lg === "uefa_champs_league" || lg === "ucl";
  return lg === L;
}

function filterOpportunities(
  opportunities: HistoryRecord[],
  since: Date,
  until: Date,
  sport: string,
  league: string,
): HistoryRecord[] {
  const t0 = since.getTime();
  const t1 = until.getTime();
  return opportunities.filter((o) => {
    const t = new Date(o.firstSeenAt).getTime();
    if (t < t0 || t > t1) return false;
    if (!matchesSport(o, sport)) return false;
    if (!matchesLeague(o, league)) return false;
    return true;
  });
}

function bucketKey(date: string, bucketUnit: "hour" | "day"): string {
  const d = new Date(date);
  if (bucketUnit === "hour") {
    d.setMinutes(0, 0, 0);
    return d.toISOString();
  }
  d.setHours(0, 0, 0, 0);
  return d.toISOString();
}

function aggregateBuckets(
  opportunities: HistoryRecord[],
  bucketUnit: "hour" | "day",
) {
  const map = new Map<
    string,
    { time: string; count: number; profitSum: number; maxProfit: number }
  >();
  for (const o of opportunities) {
    const key = bucketKey(o.firstSeenAt, bucketUnit);
    if (!map.has(key)) {
      map.set(key, { time: key, count: 0, profitSum: 0, maxProfit: 0 });
    }
    const b = map.get(key)!;
    b.count += 1;
    b.profitSum += o.profitPercent;
    b.maxProfit = Math.max(b.maxProfit, o.profitPercent);
  }
  return [...map.values()].map((b) => ({
    time: b.time,
    count: b.count,
    avgProfit: b.count
      ? Math.round((b.profitSum / b.count) * 100) / 100
      : 0,
    maxProfit: Math.round(b.maxProfit * 100) / 100,
  }));
}

function padTodayHourlyBuckets(
  buckets: Array<{
    time: string;
    count: number;
    avgProfit: number;
    maxProfit: number;
  }>,
  since: Date,
) {
  const byHour = new Map<number, (typeof buckets)[0]>();
  for (const b of buckets) {
    byHour.set(new Date(b.time).getHours(), b);
  }
  const dayStart = startOfLocalDay(since);
  const out: Array<{
    time: string;
    hour: number;
    label: string;
    count: number;
    avgProfit: number;
    maxProfit: number;
  }> = [];
  for (let h = 0; h < 24; h++) {
    const t = new Date(dayStart);
    t.setHours(h, 0, 0, 0);
    const existing = byHour.get(h);
    out.push({
      time: t.toISOString(),
      hour: h,
      label: hourLabel12(h),
      count: existing?.count ?? 0,
      avgProfit: existing?.avgProfit ?? 0,
      maxProfit: existing?.maxProfit ?? 0,
    });
  }
  return out;
}

function buildSummary(opportunities: HistoryRecord[]) {
  if (!opportunities.length) {
    return {
      totalOpportunities: 0,
      avgProfit: 0,
      bestProfit: 0,
      avgDurationMinutes: 0,
    };
  }
  let profitSum = 0;
  let durSum = 0;
  let best = 0;
  for (const o of opportunities) {
    profitSum += o.profitPercent;
    durSum += o.durationMinutes;
    best = Math.max(best, o.profitPercent);
  }
  const n = opportunities.length;
  return {
    totalOpportunities: n,
    avgProfit: Math.round((profitSum / n) * 100) / 100,
    bestProfit: Math.round(best * 100) / 100,
    avgDurationMinutes: Math.round(durSum / n),
  };
}

export function buildHistoryChart(
  range: string,
  sport: string,
  league: string,
  opportunities: HistoryRecord[],
) {
  const win = rangeWindow(range || "today");
  const filtered = filterOpportunities(
    opportunities,
    win.since,
    win.until,
    sport || "all",
    league || "all",
  );
  let buckets = aggregateBuckets(filtered, win.bucketUnit);

  if (win.pad24Hours) {
    buckets = padTodayHourlyBuckets(buckets, win.since);
  } else {
    buckets = buckets
      .sort((a, b) => new Date(a.time).getTime() - new Date(b.time).getTime())
      .map((b) => {
        const d = new Date(b.time);
        return {
          ...b,
          label: d.toLocaleDateString("en-US", {
            month: "short",
            day: "numeric",
          }),
        };
      });
  }

  return {
    range: range || "today",
    sport: sport || "all",
    league: league || "all",
    since: win.since.toISOString(),
    until: win.until.toISOString(),
    bucketUnit: win.bucketUnit,
    buckets,
    summary: buildSummary(filtered),
    opportunities: filtered
      .sort(
        (a, b) =>
          new Date(b.firstSeenAt).getTime() - new Date(a.firstSeenAt).getTime(),
      )
      .slice(0, 500)
      .map((o, i) => ({
        id: i + 1,
        oppId: o.oppId,
        sport: o.sport,
        league: o.league,
        homeTeam: o.homeTeam,
        awayTeam: o.awayTeam,
        market: o.market,
        profitPercent: o.profitPercent,
        firstSeenAt: o.firstSeenAt,
        lastSeenAt: o.lastSeenAt,
        durationMinutes: o.durationMinutes,
        legs: o.legs,
      })),
    sportFilters: SPORT_FILTERS,
    leagueFilters: LEAGUE_FILTERS,
  };
}
