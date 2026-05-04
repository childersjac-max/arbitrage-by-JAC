import { execSync } from "node:child_process";
import { mkdirSync, cpSync, writeFileSync, rmSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");

console.log("▶ Building dashboard...");
execSync("pnpm --filter @workspace/dashboard run build", {
  stdio: "inherit",
  cwd: root,
});

const vercelOut = join(root, ".vercel", "output");
if (existsSync(vercelOut)) rmSync(vercelOut, { recursive: true, force: true });

// Static files
const staticOut = join(vercelOut, "static");
mkdirSync(staticOut, { recursive: true });
cpSync(join(root, "artifacts", "dashboard", "dist", "public"), staticOut, {
  recursive: true,
});
console.log("▶ Static files → .vercel/output/static");

// Routes config
writeFileSync(
  join(vercelOut, "config.json"),
  JSON.stringify(
    {
      version: 3,
      routes: [
        { handle: "filesystem" },
        { src: "/(.*)", dest: "/index.html" },
      ],
    },
    null,
    2,
  ),
);

// Serverless functions
const endpoints = [
  "line-tracker/slate",
  "line-tracker/patterns",
  "nba-model/predictions",
  "nba-model/bet-log",
  "nba-model/backtest",
  "arbitrage/opportunities",
];

for (const ep of endpoints) {
  const funcDir = join(vercelOut, "functions", "api", ep + ".func");
  mkdirSync(funcDir, { recursive: true });
  cpSync(join(root, "api", ep + ".js"), join(funcDir, "index.js"));
  writeFileSync(
    join(funcDir, ".vc-config.json"),
    JSON.stringify(
      { runtime: "nodejs20.x", handler: "index.js", launcherType: "Nodejs" },
      null,
      2,
    ),
  );
}

console.log("▶ Functions → .vercel/output/functions/api/");
console.log("✓ Vercel build output ready");
