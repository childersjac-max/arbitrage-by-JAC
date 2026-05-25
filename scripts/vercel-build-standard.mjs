import { execSync } from "node:child_process";
import { cpSync, rmSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const repoRoot = join(dirname(fileURLToPath(import.meta.url)), "..");
const apiServerRoot = join(repoRoot, "artifacts", "api-server");
const staticSrc = join(repoRoot, "artifacts", "arb-finder", "dist", "public");
const handlerSrc = join(apiServerRoot, "dist", "handler.mjs");

console.log("▶ Building api-server + arb-finder...");
execSync(
  "pnpm --filter @workspace/api-server run build && pnpm --filter @workspace/arb-finder run build",
  { stdio: "inherit", cwd: repoRoot },
);

if (!existsSync(staticSrc)) {
  console.error(`Missing frontend build: ${staticSrc}`);
  process.exit(1);
}
if (!existsSync(handlerSrc)) {
  console.error(`Missing API handler build: ${handlerSrc}`);
  process.exit(1);
}

function copyPublic(dest) {
  if (existsSync(dest)) rmSync(dest, { recursive: true, force: true });
  cpSync(staticSrc, dest, { recursive: true });
  console.log(`▶ Static → ${dest}`);
}

copyPublic(join(apiServerRoot, "public"));
console.log("✓ Vercel standard build ready (public/)");
