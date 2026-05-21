-- Run once in Neon SQL editor (or any Postgres) for the Alerts feature.
CREATE TABLE IF NOT EXISTS alerts (
  id serial PRIMARY KEY,
  sport text,
  market text,
  min_profit_percent numeric(10, 4) NOT NULL DEFAULT '0',
  created_at timestamp NOT NULL DEFAULT now()
);
