#!/usr/bin/env node
/**
 * Pushes the current Replit workspace source files to a GitHub repo
 * via the GitHub Git Data API. Runs as a plain Node.js ESM script so
 * it can be invoked from bash where GITHUB_PERSONAL_ACCESS_TOKEN is set.
 *
 * Usage:
 *   node scripts/push-to-github.mjs
 */

import { readFileSync, existsSync } from "fs";
import { execSync } from "child_process";
import { join } from "path";

const PAT = process.env.GITHUB_PERSONAL_ACCESS_TOKEN;
const OWNER = "childersjac-max";
const REPO = "arbitrage-by-JAC";
const ROOT = "/home/runner/workspace";
const MESSAGE =
  process.env.PUSH_MESSAGE ?? "chore: sync from Replit workspace";

if (!PAT) {
  console.error("GITHUB_PERSONAL_ACCESS_TOKEN is not set");
  process.exit(1);
}

const BASE = `https://api.github.com/repos/${OWNER}/${REPO}`;
const HEADERS = {
  Authorization: `token ${PAT}`,
  "Content-Type": "application/json",
  Accept: "application/vnd.github+json",
  "User-Agent": "replit-bpr-push",
};

async function api(path, method = "GET", body) {
  const url = path.startsWith("http") ? path : `${BASE}${path}`;
  const res = await fetch(url, {
    method,
    headers: HEADERS,
    body: body ? JSON.stringify(body) : undefined,
  });
  const json = await res.json();
  if (!res.ok && res.status !== 404) {
    console.error(`API error ${res.status} ${method} ${path}:`, json.message ?? json);
  }
  return { status: res.status, data: json };
}

// Files to exclude from the push
function shouldExclude(f) {
  return (
    f.includes("node_modules") ||
    f.endsWith(".map") ||
    f.startsWith("dist/") ||
    f.includes("/.local/") ||
    f.startsWith(".local/") ||
    f === "scripts/push-to-github.mjs"
  );
}

async function main() {
  // 1. Get current HEAD
  const { data: ref } = await api(`/git/ref/heads/main`);
  const parentSha = ref?.object?.sha;
  if (!parentSha) {
    console.error("Could not get HEAD SHA for main branch");
    process.exit(1);
  }
  console.log("Parent commit:", parentSha);

  // 2. Collect files — git-tracked + untracked-but-not-ignored
  const gitTracked = execSync("git --no-optional-locks ls-files", { cwd: ROOT })
    .toString()
    .trim()
    .split("\n")
    .filter(Boolean);

  const gitUntracked = execSync(
    "git --no-optional-locks ls-files --others --exclude-standard",
    { cwd: ROOT },
  )
    .toString()
    .trim()
    .split("\n")
    .filter(Boolean);

  const tracked = Array.from(new Set([...gitTracked, ...gitUntracked])).filter(
    (f) => f && !shouldExclude(f),
  );

  console.log(`Creating blobs for ${tracked.length} files...`);

  // 3. Create blobs
  const treeItems = [];
  let done = 0;
  let skipped = 0;

  const delay = (ms) => new Promise((r) => setTimeout(r, ms));

  for (const filePath of tracked) {
    const absPath = join(ROOT, filePath);
    if (!existsSync(absPath)) { skipped++; continue; }

    let content, encoding;
    try {
      const buf = readFileSync(absPath);
      const isBinary = buf.slice(0, 8192).includes(0);
      content = isBinary ? buf.toString("base64") : buf.toString("utf8");
      encoding = isBinary ? "base64" : "utf-8";
    } catch {
      skipped++;
      continue;
    }

    // Retry up to 3 times with backoff to handle GitHub secondary rate limits
    let blob = null;
    for (let attempt = 1; attempt <= 3; attempt++) {
      const { data, status } = await api("/git/blobs", "POST", { content, encoding });
      if (data.sha) { blob = data; break; }
      if (status === 403 || status === 429) {
        const wait = attempt * 8000;
        console.log(`  Rate limited on ${filePath}, waiting ${wait / 1000}s (attempt ${attempt})...`);
        await delay(wait);
      } else {
        console.error(`  BLOB ERROR ${filePath}: ${data.message}`);
        break;
      }
    }

    if (!blob?.sha) { skipped++; continue; }

    treeItems.push({ path: filePath, mode: "100644", type: "blob", sha: blob.sha });
    done++;
    if (done % 40 === 0) console.log(`  ${done}/${tracked.length} blobs`);
    // Small pause every 10 files to stay under secondary rate limits
    if (done % 10 === 0) await delay(500);
  }

  console.log(`Blobs done: ${done}, skipped: ${skipped}`);

  // 4. Create tree
  const { data: tree } = await api("/git/trees", "POST", { tree: treeItems });
  if (!tree.sha) { console.error("Tree creation failed:", tree); process.exit(1); }
  console.log("Tree:", tree.sha);

  // 5. Create commit
  const { data: commit } = await api("/git/commits", "POST", {
    message: MESSAGE,
    tree: tree.sha,
    parents: [parentSha],
  });
  if (!commit.sha) { console.error("Commit failed:", commit); process.exit(1); }
  console.log("Commit:", commit.sha);

  // 6. Update main branch ref
  const { data: updated } = await api("/git/refs/heads/main", "PATCH", {
    sha: commit.sha,
    force: false,
  });
  console.log("Branch updated:", updated?.object?.sha);
  console.log(`\nDone! https://github.com/${OWNER}/${REPO}`);
}

main().catch((e) => { console.error(e); process.exit(1); });
