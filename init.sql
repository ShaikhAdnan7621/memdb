-- MemDB PostgreSQL Initialization Script
-- This script sets up the initial PostgreSQL configuration for MemDB

-- Create database if it doesn't exist
SELECT 'CREATE DATABASE memdb_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'memdb_db')\gexec

-- Connect to the database
\c memdb_db

-- Create schema
CREATE SCHEMA IF NOT EXISTS memdb;

-- Set search path
SET search_path TO memdb, public;

-- Create base tables for MemDB
-- Note: MemDB creates table dynamically, but this provides examples

-- Example: Users table with JSONB
CREATE TABLE IF NOT EXISTS memdb_users (
    key TEXT PRIMARY KEY,
    data JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create GIN index for JSONB queries
CREATE INDEX IF NOT EXISTS idx_memdb_users_data ON memdb_users USING GIN (data);

-- Example: Sessions table with JSONB
CREATE TABLE IF NOT EXISTS memdb_sessions (
    key TEXT PRIMARY KEY,
    data JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_memdb_sessions_data ON memdb_sessions USING GIN (data);

-- Example: Calls table for telephony
CREATE TABLE IF NOT EXISTS memdb_calls (
    key TEXT PRIMARY KEY,
    data JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_memdb_calls_data ON memdb_calls USING GIN (data);
CREATE INDEX IF NOT EXISTS idx_memdb_calls_status ON memdb_calls ((data->>'status'));

-- Grants (if using specific user)
ALTER SCHEMA memdb OWNER TO memdb_user;

-- Grant permissions
GRANT ALL PRIVILEGES ON SCHEMA memdb TO memdb_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA memdb TO memdb_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA memdb TO memdb_user;

-- Set default privileges for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA memdb GRANT ALL ON TABLES TO memdb_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA memdb GRANT ALL ON SEQUENCES TO memdb_user;

-- Enable extensions that might be useful
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Display info
SELECT 'MemDB PostgreSQL initialization complete!' as status;
SELECT version();
