"""Schema DDL and filesystem paths for demo seed CSVs."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DEMO_DATA_DIR = REPO_ROOT / "backend" / "data" / "demo"

INVENTORY_DDL = """
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
"""
