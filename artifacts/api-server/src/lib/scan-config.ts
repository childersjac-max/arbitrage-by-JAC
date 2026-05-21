/** OpticOdds sport + league pairs included in the arbitrage scan loop. */
export interface ScanTarget {
  sport: string;
  leagues: string[];
}

export const SCAN_TARGETS: ScanTarget[] = [
  { sport: "baseball", leagues: ["mlb"] },
  { sport: "basketball", leagues: ["nba", "wnba"] },
  { sport: "football", leagues: ["nfl"] },
  { sport: "hockey", leagues: ["nhl"] },
  { sport: "golf", leagues: ["pga"] },
  { sport: "soccer", leagues: ["mls", "epl", "uefa_champs_league"] },
];

export const MAJOR_SPORT_KEYS = [
  "baseball",
  "basketball",
  "football",
  "hockey",
  "golf",
  "soccer",
  "tennis",
  "mma",
] as const;
