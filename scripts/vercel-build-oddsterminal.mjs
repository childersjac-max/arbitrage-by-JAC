import { execSync } from "node:child_process";
import { mkdirSync, cpSync, writeFileSync, rmSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const repoRoot = join(dirname(fileURLToPath(import.meta.url)), "..");

console.log("▶ Building api-server + arb-finder...");
execSync(
  "pnpm --filter @workspace/api-server run build && pnpm --filter @workspace/arb-finder run build",
  { stdio: "inherit", cwd: repoRoot },
);

const staticSrc = join(repoRoot, "artifacts", "arb-finder", "dist", "public");
const handlerSrc = join(repoRoot, "artifacts", "api-server", "dist", "handler.mjs");

if (!existsSync(staticSrc)) {
  console.error(`Missing frontend build: ${staticSrc}`);
  process.exit(1);
}
if (!existsSync(handlerSrc)) {
  console.error(`Missing API handler build: ${handlerSrc}`);
  process.exit(1);
}

function writeBuildOutput(vercelOut) {
  if (existsSync(vercelOut)) rmSync(vercelOut, { recursive: true, force: true });

  const staticOut = join(vercelOut, "static");
  mkdirSync(staticOut, { recursive: true });
  cpSync(staticSrc, staticOut, { recursive: true });

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
}

function copyPublic(destPublic) {
  if (existsSync(destPublic)) rmSync(destPublic, { recursive: true, force: true });
  cpSync(staticSrc, destPublic, { recursive: true });
  console.log(`▶ Static files → ${destPublic}`);
}

// Vercel resolves output relative to Project Root Directory (often artifacts/api-server).
const outputTargets = [
  join(repoRoot, ".vercel", "output"),
  join(repoRoot, "artifacts", "api-server", ".vercel", "output"),
  join(repoRoot, "artifacts", "arb-finder", ".vercel", "output"),
];

const publicTargets = [
  join(repoRoot, "public"),
  join(repoRoot, "artifacts", "api-server", "public"),
  join(repoRoot, "artifacts", "arb-finder", "public"),
];

for (const out of outputTargets) {
  writeBuildOutput(out);
  console.log(`▶ Build Output API → ${out}`);
}

for (const pub of publicTargets) {
  mkdirSync(dirname(pub), { recursive: true });
  copyPublic(pub);
}

console.log("✓ Vercel deploy artifacts ready");
