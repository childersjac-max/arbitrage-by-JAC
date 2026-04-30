import { Router, type IRouter } from "express";

const router: IRouter = Router();

router.get("/diagnostics", async (req, res): Promise<void> => {
  const apiKey = process.env["ODDSJAM_API_KEY"];
  const results: Record<string, unknown> = {
    apiKeySet: !!apiKey,
    apiKeyLength: apiKey?.length ?? 0,
    nodeVersion: process.version,
    timestamp: new Date().toISOString(),
  };

  const testUrls = [
    "https://api.oddsjam.com/api/v2/sports",
    "https://jsonplaceholder.typicode.com/todos/1",
  ];

  for (const url of testUrls) {
    const key = url.includes("oddsjam") ? "oddsjam" : "jsonplaceholder";
    try {
      const headers: Record<string, string> = {};
      if (url.includes("oddsjam") && apiKey) headers["x-api-key"] = apiKey;
      const r = await fetch(url, { headers, signal: AbortSignal.timeout(8000) });
      const text = await r.text().catch(() => "");
      results[key] = { ok: r.ok, status: r.status, bodyPreview: text.slice(0, 200) };
    } catch (err: unknown) {
      const e = err as Error & { cause?: { code?: string; message?: string } };
      results[key] = {
        ok: false,
        error: e.message,
        cause: e.cause ? { code: e.cause.code, message: e.cause.message } : undefined,
      };
    }
  }

  res.json(results);
});

export default router;
