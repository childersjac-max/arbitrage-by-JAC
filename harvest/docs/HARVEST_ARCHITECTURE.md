# Harvest architecture

## Objective

Unify 14 logical data targets into one arbitrage board by:

1. **Parallel extraction** (thread pool per source)
2. **Splicing** metadata-rich sportsbook fixtures with prediction-market prices
3. **Fuzzy entity resolution** so `Charlotte Hornets`, `Hornets`, and `CHA Hornets` align
4. **Normalization** into a single JSON schema with cross-source yield %

## Layered fallback matrix (compliant)

| Layer | Mechanism | When used |
|-------|-----------|-----------|
| **A — HTTP API** | `httpx` + retries/jitter (`resilience.py`) | Public or API-keyed JSON endpoints |
| **B — Official SDK / session** | Betfair JSON-RPC with app key + session token | Exchange order books |
| **C — Cached / degraded** | Return last good snapshot (extend in orchestrator) | Upstream outage |

We **do not** implement a “stealth browser” tier to defeat Cloudflare, PerimeterX, or similar. If an endpoint returns 403 without credentials, the fix is: obtain legal API access or reduce request rate — not fingerprint evasion.

## Module map

```
harvest/
  config.py           # env, scan targets, NC sportsbooks list
  fuzzy.py            # RapidFuzz + alias table for teams
  odds_math.py        # American ↔ decimal, arb yield
  resilience.py       # 429/5xx backoff + jitter
  extractors/         # one profile per platform family
  splice.py           # merge fragments by event identity
  normalize.py        # emit UnifiedArbitrageRow list
  orchestrator.py     # ThreadPoolExecutor coordinator
  pipeline.py         # CLI entry
```

## Splicing technique

Production pain: Optic Odds fixtures carry **accurate team names and leagues**; Kalshi/Polymarket titles are **noisy but fast**.

1. Collect all `MarketFragment` rows.
2. Build `EventIdentity` key: `sport|league|away@home` (slugged, sorted).
3. Pick canonical metadata from sportsbook rows (`prefer_metadata_source`).
4. Re-write prediction-market rows with `sport=unknown` to inherit home/away/league.
5. `attach_kalshi_to_sportsbook_fragments()` adds Kalshi legs only when fuzzy title matches both teams.

## Fuzzy matching

- `normalize_team_name()` strips accents, cities, and applies `ALIASES` (e.g. `CHA` → `hornets`).
- `match_event_titles()` uses `rapidfuzz.partial_ratio` ≥ threshold (default 82).
- False-positive guard: require **both** team tokens in haystack before merge.

## Node.js parity

`artifacts/api-server/src/lib/scanner.ts` runs the same merge pattern:

- Optic Odds → `oddsjam.ts`
- Kalshi → `kalshi.ts`
- Polymarket → `prediction-markets.ts`

## Running continuously

- Schedule `python3 -m harvest` via cron/systemd every 30–60s.
- Or rely on the Express monitor (`monitor.ts`) which already scans on an interval and writes `arb_history`.

For sub-second latency, use vendor **streaming** products (Optic Odds streams, Betfair stream API) — not HTML scraping.
