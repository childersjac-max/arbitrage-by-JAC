import {
  integer,
  jsonb,
  pgTable,
  real,
  serial,
  text,
  timestamp,
  varchar,
} from "drizzle-orm/pg-core";

export const arbHistoryTable = pgTable("arb_history", {
  id: serial("id").primaryKey(),
  oppId: varchar("opp_id", { length: 255 }).notNull().unique(),
  sport: varchar("sport", { length: 64 }).notNull(),
  league: varchar("league", { length: 64 }),
  homeTeam: text("home_team").notNull(),
  awayTeam: text("away_team").notNull(),
  market: varchar("market", { length: 128 }).notNull(),
  profitPercent: real("profit_percent").notNull(),
  legs: jsonb("legs").notNull().$type<unknown[]>(),
  firstSeenAt: timestamp("first_seen_at", { withTimezone: true }).notNull(),
  lastSeenAt: timestamp("last_seen_at", { withTimezone: true }).notNull(),
  durationMinutes: integer("duration_minutes").notNull().default(0),
});

export type ArbHistoryRow = typeof arbHistoryTable.$inferSelect;
