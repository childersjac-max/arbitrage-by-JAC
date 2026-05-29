import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { logger } from "./logger";

const CACHE_TTL_MS = 45_000;

let cached: Record<string, unknown> | null = null;
let cachedAt = 0;
let runInFlight: Promise<Record<string, unknown>> | null = null;

function repoRoot(): string {
  const here = dirname(fileURLToPath(import.meta.url));
  // artifacts/api-server/dist or src → workspace root
  const candidates = [
    join(here, "../../../.."),
    join(here, "../../.."),
    process.cwd(),
  ];
  for (const c of candidates) {
    if (existsSync(join(c, "arb-harvest", "arb_harvest", "__main__.py"))) {
      return c;
    }
  }
  return process.cwd();
}

export function isArbHarvestAvailable(): boolean {
  const root = repoRoot();
  return existsSync(join(root, "arb-harvest", "arb_harvest", "__main__.py"));
}

export async function runArbHarvest(options?: {
  refresh?: boolean;
}): Promise<Record<string, unknown>> {
  const now = Date.now();
  if (
    !options?.refresh &&
    cached &&
    now - cachedAt < CACHE_TTL_MS
  ) {
    return cached;
  }
  if (runInFlight) return runInFlight;

  runInFlight = (async () => {
    if (!process.env["ODDS_API_KEY"]) {
      return {
        timestamp: new Date().toISOString(),
        error: "ODDS_API_KEY not set",
        event_count: 0,
        arbitrage_signals: [],
      };
    }
    if (!isArbHarvestAvailable()) {
      return {
        timestamp: new Date().toISOString(),
        error: "arb-harvest package not found in workspace",
        event_count: 0,
        arbitrage_signals: [],
      };
    }

    const root = repoRoot();
    const payload = await new Promise<Record<string, unknown>>((resolve, reject) => {
      const child = spawn("python3", ["-m", "arb_harvest", "--once"], {
        cwd: join(root, "arb-harvest"),
        env: { ...process.env },
        stdio: ["ignore", "pipe", "pipe"],
      });
      let stdout = "";
      let stderr = "";
      child.stdout.on("data", (c: Buffer) => {
        stdout += c.toString();
      });
      child.stderr.on("data", (c: Buffer) => {
        stderr += c.toString();
      });
      child.on("close", (code) => {
        if (code !== 0) {
          logger.warn({ code, stderr: stderr.slice(0, 500) }, "arb-harvest exited non-zero");
          reject(new Error(stderr || `arb-harvest exit ${code}`));
          return;
        }
        try {
          resolve(JSON.parse(stdout) as Record<string, unknown>);
        } catch (e) {
          reject(new Error(`Invalid JSON from arb-harvest: ${String(e)}`));
        }
      });
    });

    cached = payload;
    cachedAt = Date.now();
    return payload;
  })().finally(() => {
    runInFlight = null;
  });

  return runInFlight;
}
