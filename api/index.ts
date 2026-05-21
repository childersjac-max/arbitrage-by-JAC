import type { VercelRequest, VercelResponse } from "@vercel/node";
import serverless from "serverless-http";
import app from "../artifacts/api-server/src/app";

const handler = serverless(app, {
  binary: false,
});

export default async function (
  req: VercelRequest,
  res: VercelResponse,
): Promise<unknown> {
  return handler(req, res);
}
