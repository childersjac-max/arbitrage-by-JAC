/**
 * src/lib/api-base.ts
 *
 * Single source of truth for the API base URL.
 *
 * - On Vercel (production):  VITE_API_BASE_URL is empty ("") → all calls are
 *   relative (e.g. "/api/config"), which Vercel routes to its serverless functions.
 *
 * - In local dev:            VITE_API_BASE_URL is also empty (""), but vite.config.ts
 *   proxies /api/* → http://localhost:3001, so the Express dev server handles them.
 *
 * - If you ever self-host with a separate API domain, set:
 *   VITE_API_BASE_URL=https://api.yourdomain.com
 *   and all fetch calls will automatically use that origin.
 */
export const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '';

/**
 * Convenience wrapper: resolves a path relative to the API base.
 *
 * Usage:
 *   apiUrl('/api/config')         → '/api/config'        (Vercel / dev proxy)
 *   apiUrl('/api/alerts')         → '/api/alerts'
 *   apiUrl('/api/config', true)   → full URL logged to console (debug helper)
 */
export function apiUrl(path: string, debug = false): string {
  const url = `${API_BASE}${path}`;
  if (debug) console.debug('[api-base] resolved:', url);
  return url;
}
