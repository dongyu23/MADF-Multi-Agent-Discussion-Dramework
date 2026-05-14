-- MADF initial database setup
-- Executed automatically by docker-entrypoint-initdb.d

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Database and user are already created via POSTGRES_USER/POSTGRES_DB env vars.
-- Additional extensions or seed data can be added here.
