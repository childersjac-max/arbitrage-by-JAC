import { cpSync, rmSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const src = join(root, "artifacts", "arb-finder", "dist", "public");

if (!existsSync(src)) {
  console.error(`Build output not found: ${src}`);
  process.exit(1);
}

// Vercel Output Directory is relative to Project Root Directory in the dashboard.
// Copy to every location we use so either repo root or artifacts/arb-finder works.
const targets = [
  join(root, "public"),
  join(root, "artifacts", "arb-finder", "public"),
];

for (const dest of targets) {
  rmSync(dest, { recursive: true, force: true });
  cpSync(src, dest, { recursive: true });
  console.log(`▶ Copied ${src} → ${dest}`);
}
