-- TSOC PostgreSQL schema
-- Apply manually with:
--   psql "postgresql://user:pass@host:5432/dbname" -f backend/db/schema.sql

BEGIN;

CREATE TABLE IF NOT EXISTS tsoc_records (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    tsoc_record_type TEXT NOT NULL,
    sid TEXT NULL,
    search_name TEXT NULL,
    row_index INTEGER NULL,
    payload JSONB NOT NULL
);

-- Upgrade older DBs created before row_index existed
ALTER TABLE tsoc_records ADD COLUMN IF NOT EXISTS row_index INTEGER NULL;

CREATE INDEX IF NOT EXISTS idx_tsoc_records_type_created
    ON tsoc_records (tsoc_record_type, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_tsoc_records_sid_created
    ON tsoc_records (sid, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_tsoc_records_sid_row_created
    ON tsoc_records (sid, row_index, created_at DESC);

CREATE TABLE IF NOT EXISTS tsoc_users (
    user_id TEXT PRIMARY KEY,
    display_name TEXT,
    email TEXT,
    department TEXT,
    risk_score INTEGER NOT NULL DEFAULT 0,
    description TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS tsoc_assets (
    asset_id TEXT PRIMARY KEY,
    asset_type TEXT NOT NULL,
    hostname TEXT,
    fqdn TEXT,
    ip TEXT,
    owner TEXT,
    criticality TEXT NOT NULL DEFAULT 'medium',
    risk_score INTEGER NOT NULL DEFAULT 0,
    description TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS tsoc_relationships (
    relationship_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    asset_id TEXT NOT NULL,
    description TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, asset_id)
);

ALTER TABLE tsoc_relationships DROP COLUMN IF EXISTS relationship_type;

CREATE INDEX IF NOT EXISTS idx_tsoc_relationships_user
    ON tsoc_relationships (user_id);

CREATE INDEX IF NOT EXISTS idx_tsoc_relationships_asset
    ON tsoc_relationships (asset_id);

CREATE TABLE IF NOT EXISTS tsoc_rag_documents (
    doc_id TEXT PRIMARY KEY,
    doc_type TEXT NOT NULL,
    sid TEXT NULL,
    search_name TEXT NULL,
    row_index INTEGER NOT NULL DEFAULT 0,
    essential JSONB NOT NULL DEFAULT '{}'::jsonb,
    summary_line TEXT NOT NULL DEFAULT '',
    chunk_text TEXT NOT NULL DEFAULT '',
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_tsoc_rag_docs_sid ON tsoc_rag_documents (sid);
CREATE INDEX IF NOT EXISTS idx_tsoc_rag_docs_type_updated ON tsoc_rag_documents (doc_type, updated_at DESC);

COMMIT;
