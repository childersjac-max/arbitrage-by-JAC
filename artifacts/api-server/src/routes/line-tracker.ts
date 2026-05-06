import { Router, type IRouter } from "express";

const router: IRouter = Router();

const LT_RAW =
  "https://raw.githubusercontent.com/childersjac-max/Line-Tracker-Model/main";

// In-memory cache — survives across requests in the same process
let _slateCache: { bets: unknown[]; total: number; fetched_at: string } | null = null;
let _slateCacheTime = 0;
const SLATE_CACHE_TTL = 45_000; // 45 seconds

function parseCSV(text: string): Record<string, string>[] {
  const lines = text.trim().split(/\r?\n/);
  if (lines.length < 2) return [];
  const headers = splitCSVRow(lines[0]);
  return lines.slice(1).map((line) => {
    const vals = splitCSVRow(line);
    const obj: Record<string, string> = {};
    headers.forEach((h, i) => {
      obj[h.trim()] = (vals[i] || "").trim();
    });
    return obj;
  });
}

function splitCSVRow(line: string): string[] {
  const result: string[] = [];
  let cur = "";
  let inQuote = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (ch === '"') {
      if (inQuote && line[i + 1] === '"') {
        cur += '"';
        i++;
      } else {
        inQuote = !inQuote;
      }
    } else if (ch === "," && !inQuote) {
      result.push(cur);
      cur = "";
    } else {
      cur += ch;
    }
  }
  result.push(cur);
  return result;
}

function castBet(row: Record<string, string>) {
  const numFields = [
    "model_prob",
    "fair_prob",
    "edge_pct",
    "ev_pct",
    "bet_pct",
    "bet_usd",
    "american_odds",
    "n_signals",
    "hours_to_game",
    "side_injury_score",
    "opp_injury_score",
    "arb_margin_pct",
  ];
  const out: Record<string, unknown> = { ...row };
  for (const f of numFields) {
    if (out[f] !== undefined && out[f] !== "") {
      const n = parseFloat(out[f] as string);
      if (!isNaN(n)) out[f] = n;
    }
  }
  return out;
}

async function fetchText(url: string): Promise<string> {
  const res = await fetch(url + `?t=${Date.now()}`, { cache: "no-store" } as RequestInit);
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${url}`);
  return res.text();
}

router.get("/line-tracker/slate", async (req, res) => {
  // Serve in-process cache if still fresh
  if (_slateCache && Date.now() - _slateCacheTime < SLATE_CACHE_TTL) {
    return res.json(_slateCache);
  }

  try {
    const text = await fetchText(`${LT_RAW}/pipeline_output/bet_slate_latest.csv`);
    const rows = parseCSV(text);
    const bets = rows
      .filter((r) => r.sport && r.sport.trim() !== "")
      .map(castBet);

    // Only cache when we get real data — never replace good cache with empty result
    if (bets.length > 0) {
      _slateCache = { bets, total: bets.length, fetched_at: new Date().toISOString() };
      _slateCacheTime = Date.now();
    }

    // If pipeline returned 0 rows but we have prior good data, serve it
    if (bets.length === 0 && _slateCache) {
      return res.json(_slateCache);
    }

    res.json({ bets, total: bets.length, fetched_at: new Date().toISOString() });
  } catch (e: unknown) {
    req.log.error({ err: e }, "Failed to fetch line tracker slate");
    if (_slateCache) {
      return res.json(_slateCache);
    }
    res.status(500).json({
      error: "fetch_failed",
      message: e instanceof Error ? e.message : String(e),
    });
  }
});

router.get("/line-tracker/patterns", async (req, res) => {
  try {
    const r = await fetch(`${LT_RAW}/pipeline_output/patterns.json?t=${Date.now()}`, { cache: "no-store" } as RequestInit);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const data = await r.json();
    res.json(data);
  } catch (e: unknown) {
    req.log.error({ err: e }, "Failed to fetch patterns");
    res.status(500).json({
      error: "fetch_failed",
      message: e instanceof Error ? e.message : String(e),
    });
  }
});

export default router;
