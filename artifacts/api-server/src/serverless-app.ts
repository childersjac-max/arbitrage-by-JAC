import express, { type Express } from "express";
import cors from "cors";
import router from "./routes";

/** Express app for Vercel — no pino-http (worker threads break serverless). */
const app: Express = express();

app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use("/api", router);

export default app;
