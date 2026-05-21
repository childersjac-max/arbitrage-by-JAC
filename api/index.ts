import serverless from "serverless-http";
// Pre-built by `pnpm --filter @workspace/api-server run build` (see build.mjs → dist/serverless.mjs)
import app from "../artifacts/api-server/dist/serverless.mjs";

const handler = serverless(app, { binary: false });

export default handler;
