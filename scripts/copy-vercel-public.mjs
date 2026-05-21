import { cpSync, rmSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const src = join(root, "artifacts", "arb-finder", "dist", "public");
const dest = join(root, "public");

if (!existsSync(src)) {
  console.error(`Build output not found: ${src}`);
  process.exit(1);
}

rmSync(dest, { recursive: true, force: true });
cpSync(src, dest, { recursive: true });
console.log(`▶ Copied ${src} → ${dest}`);
