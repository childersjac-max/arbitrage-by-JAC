#!/bin/bash
# Optional hook after git merge/pull. Never fail the Repl environment build.
pnpm install --frozen-lockfile 2>/dev/null || pnpm install 2>/dev/null || true
if [ -n "${DATABASE_URL:-}" ]; then
  pnpm --filter @workspace/db run push 2>/dev/null || echo "post-merge: db push skipped or failed"
fi
exit 0
