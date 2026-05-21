import { drizzle, type NodePgDatabase } from "drizzle-orm/node-postgres";
import pg from "pg";
import * as schema from "./schema";

const { Pool } = pg;

let pool: pg.Pool | null = null;
let dbInstance: NodePgDatabase<typeof schema> | null = null;

function getDbInstance(): NodePgDatabase<typeof schema> {
  const url = process.env.DATABASE_URL;
  if (!url) {
    throw new Error(
      "DATABASE_URL must be set. Did you forget to provision a database?",
    );
  }
  if (!dbInstance) {
    pool = new Pool({ connectionString: url });
    dbInstance = drizzle(pool, { schema });
  }
  return dbInstance;
}

export const db = new Proxy({} as NodePgDatabase<typeof schema>, {
  get(_target, prop, receiver) {
    return Reflect.get(getDbInstance(), prop, receiver);
  },
});

export * from "./schema";
