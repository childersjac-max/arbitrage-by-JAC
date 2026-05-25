import { execSync } from "node:child_process";
import { mkdirSync, cpSync, writeFileSync, rmSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");

console.log("▶ Building api-server + arb-finder...");
execSync(
  "pnpm --filter @workspace/api-server run build && pnpm --filter @workspace/arb-finder run build",
  { stdio: "inherit", cwd: root },
);

const staticSrc = join(root, "artifacts", "arb-finder", "dist", "public");
const handlerSrc = join(root, "artifacts", "api-server", "dist", "handler.mjs");

if (!existsSync(staticSrc)) {
  console.error(`Missing frontend build: ${staticSrc}`);
  process.exit(1);
}
if (!existsSync(handlerSrc)) {
  console.error(`Missing API handler build: ${handlerSrc}`);
  process.exit(1);
}

const vercelOut = join(root, ".vercel", "output");
if (existsSync(vercelOut)) rmSync(vercelOut, { recursive: true, force: true });

// Static SPA
const staticOut = join(vercelOut, "static");
mkdirSync(staticOut, { recursive: true });
cpSync(staticSrc, staticOut, { recursive: true });
console.log("▶ Static files → .vercel/output/static");

// Routing: API first, then SPA fallback
writeFileSync(
  join(vercelOut, "config.json"),
  JSON.stringify(
    {
      version: 3,
      routes: [
        { src: "/api(?:/(.*))?", dest: "/api" },
        { handle: "filesystem" },
        { src: "/(.*)", dest: "/index.html" },
      ],
    },
    null,
    2,
  ),
);

// Express API (all /api/* routes)
const funcDir = join(vercelOut, "functions", "api.func");
mkdirSync(funcDir, { recursive: true });
cpSync(handlerSrc, join(funcDir, "index.mjs"));
writeFileSync(
  join(funcDir, ".vc-config.json"),
  JSON.stringify(
    {
      runtime: "nodejs24.x",
      handler: "index.mjs",
      launcherType: "Nodejs",
      maxDuration: 60,
    },
    null,
    2,
  ),
);

console.log("▶ API handler → .vercel/output/functions/api.func");
console.log("✓ Vercel Build Output ready");
