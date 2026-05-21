import serverless from "serverless-http";
import app from "../../api-server/dist/serverless.mjs";

const handler = serverless(app, { binary: false });

export default handler;
