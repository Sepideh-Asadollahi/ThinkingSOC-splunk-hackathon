"""Export/restore full PostgreSQL demo state from backend/data/demo/postgres_snapshot/."""

from __future__ import annotations

import json
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence
from uuid import UUID

from config import Settings
from services.inventory.constants import DEMO_DATA_DIR, INVENTORY_DDL
from services.splunk_json_store.pg import jsonb_param

logger = logging.getLogger(__name__)

SNAPSHOT_DIR = DEMO_DATA_DIR / "postgres_snapshot"
MANIFEST_FILE = "manifest.json"

# Committed full demo bundle: inventory, analyses, findings, RAG, Chat, and Runbooks.
DEMO_RECORD_LIMIT = 6

# Correlation page (/correlation) = graph_findings: include only the newest finding.
DEMO_CORRELATION_LIMIT = 1

# Always export all rows (Asset + Identity inventory).
FULL_EXPORT_TABLES: frozenset[str] = frozenset(
    {
        "tsoc_users",
        "tsoc_assets",
        "tsoc_relationships",
        "tsoc_identity_rules",
    }
)

# Time-ordered tables exported as "newest N" instead of all rows.
LIMITED_EXPORT_TABLES: frozenset[str] = frozenset({"tsoc_records", "graph_findings"})

# Insert order respects FK (chat messages → conversations).
SNAPSHOT_TABLE_ORDER: Sequence[str] = (
    "tsoc_users",
    "tsoc_assets",
    "tsoc_relationships",
    "tsoc_identity_rules",
    "tsoc_records",
    "tsoc_rag_documents",
    "graph_findings",
    "tsoc_chat_conversations",
    "tsoc_chat_messages",
)

_IDENTITY_RULES_DDL = """
CREATE TABLE IF NOT EXISTS tsoc_identity_rules (
    rule_id TEXT PRIMARY KEY,
    priority INTEGER NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT true,
    entity_type TEXT NOT NULL,
    alert_field TEXT NOT NULL,
    inventory_lookup TEXT NOT NULL,
    inventory_field TEXT NOT NULL,
    match_type TEXT NOT NULL DEFAULT 'exact',
    on_multiple_matches TEXT NOT NULL DEFAULT 'first',
    description TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_tsoc_identity_rules_enabled ON tsoc_identity_rules (enabled);
CREATE INDEX IF NOT EXISTS idx_tsoc_identity_rules_priority ON tsoc_identity_rules (priority);
"""

_RAG_DDL = """
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
"""

_RECORDS_DDL = """
CREATE TABLE IF NOT EXISTS tsoc_records (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    tsoc_record_type TEXT NOT NULL,
    sid TEXT NULL,
    search_name TEXT NULL,
    row_index INTEGER NULL,
    payload JSONB NOT NULL
);
ALTER TABLE tsoc_records ADD COLUMN IF NOT EXISTS row_index INTEGER NULL;
CREATE INDEX IF NOT EXISTS idx_tsoc_records_type_created
    ON tsoc_records (tsoc_record_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_tsoc_records_sid_created
    ON tsoc_records (sid, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_tsoc_records_sid_row_created
    ON tsoc_records (sid, row_index, created_at DESC);
"""

_GRAPH_FINDINGS_DDL = """
CREATE TABLE IF NOT EXISTS graph_findings (
    id UUID PRIMARY KEY,
    finding_type VARCHAR(64) NOT NULL,
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    risk_score INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(32) NOT NULL DEFAULT 'open',
    ticket_status VARCHAR(32) NOT NULL DEFAULT 'open',
    owner VARCHAR(128) NOT NULL DEFAULT 'unassigned',
    display_id VARCHAR(32),
    agent_validation_status VARCHAR(64),
    content_hash VARCHAR(128),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_graph_findings_type ON graph_findings (finding_type);
CREATE INDEX IF NOT EXISTS idx_graph_findings_risk ON graph_findings (risk_score DESC);
CREATE INDEX IF NOT EXISTS idx_graph_findings_content_hash ON graph_findings (content_hash);
"""

_CHAT_DDL = """
CREATE TABLE IF NOT EXISTS tsoc_chat_conversations (
    conversation_id TEXT PRIMARY KEY,
    title TEXT NOT NULL DEFAULT 'New chat',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_tsoc_chat_conv_updated
    ON tsoc_chat_conversations (updated_at DESC);
CREATE TABLE IF NOT EXISTS tsoc_chat_messages (
    message_id BIGSERIAL PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES tsoc_chat_conversations(conversation_id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    seq INTEGER NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (conversation_id, seq)
);
CREATE INDEX IF NOT EXISTS idx_tsoc_chat_msg_conv_seq
    ON tsoc_chat_messages (conversation_id, seq);
"""


def resolve_snapshot_dir(demo_data_dir: Optional[Path] = None) -> Path:
    base = demo_data_dir if demo_data_dir is not None else DEMO_DATA_DIR
    return base / "postgres_snapshot"


def snapshot_available(demo_data_dir: Optional[Path] = None) -> bool:
    return (resolve_snapshot_dir(demo_data_dir) / MANIFEST_FILE).is_file()


def _json_default(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    return str(value)


def _serialize_row(row: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for key, value in dict(row).items():
        if isinstance(value, (datetime, date)):
            out[key] = value.isoformat()
        elif isinstance(value, UUID):
            out[key] = str(value)
        else:
            out[key] = value
    return out


def _prepare_bind(column: str, value: Any, *, table: str = "") -> Any:
    if value is None:
        return None
    if column in ("payload", "essential", "metadata", "details"):
        if isinstance(value, (dict, list)):
            return jsonb_param(value)
        return value
    if isinstance(value, str):
        if column == "id" and table == "graph_findings":
            return UUID(value)
        if column.endswith("_at") or column in ("created_at", "updated_at"):
            text = value.replace("Z", "+00:00")
            return datetime.fromisoformat(text)
    return value


async def ensure_snapshot_schema(conn: Any) -> None:
    """Create all tables that may appear in a demo snapshot."""
    for block in (
        _RECORDS_DDL,
        INVENTORY_DDL,
        _IDENTITY_RULES_DDL,
        _RAG_DDL,
        _GRAPH_FINDINGS_DDL,
        _CHAT_DDL,
    ):
        await conn.execute(block)


async def _inventory_empty(conn: Any) -> bool:
    n_users = await conn.fetchval("SELECT COUNT(*) FROM tsoc_users")
    n_assets = await conn.fetchval("SELECT COUNT(*) FROM tsoc_assets")
    n_rels = await conn.fetchval("SELECT COUNT(*) FROM tsoc_relationships")
    return not (n_users or n_assets or n_rels)


def _expected_rows_from_manifest(manifest: Dict[str, Any]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for entry in manifest.get("tables", []):
        name = entry.get("name")
        rows = entry.get("rows")
        if name and rows is not None:
            out[str(name)] = int(rows)
    return out


async def _demo_bundle_needs_load(conn: Any, manifest_path: Path) -> bool:
    if not manifest_path.is_file():
        return False
    if await _inventory_empty(conn):
        return True
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = _expected_rows_from_manifest(manifest)
    for table, want in expected.items():
        try:
            have = int(await conn.fetchval(f'SELECT COUNT(*) FROM "{table}"') or 0)
        except Exception:
            return True
        if have < want:
            logger.info(
                "postgres_snapshot %s has %d rows, want %d — re-seed needed",
                table,
                have,
                want,
            )
            return True
    return False


async def _truncate_demo_snapshot_tables(conn: Any) -> None:
    for table in reversed(SNAPSHOT_TABLE_ORDER):
        try:
            await conn.execute(f'TRUNCATE TABLE "{table}" CASCADE')
        except Exception:
            pass


async def export_postgres_snapshot(
    settings: Settings,
    *,
    out_dir: Optional[Path] = None,
    record_limit: int = DEMO_RECORD_LIMIT,
    correlation_limit: int = DEMO_CORRELATION_LIMIT,
    full: bool = False,
) -> Path:
    """Export demo PostgreSQL state to JSON files under postgres_snapshot/.

    ``full=True`` (or ``record_limit <= 0`` and ``correlation_limit <= 0``):
    every row in every SNAPSHOT_TABLE_ORDER table — no caps.

    Default (moment demo): full Asset/Identity + newest N tsoc_records +
    newest correlation findings.
    """
    from services.splunk_json_store import ensure_pool

    target = out_dir or SNAPSHOT_DIR
    target.mkdir(parents=True, exist_ok=True)

    unlimited_records = full or int(record_limit) <= 0
    unlimited_findings = full or int(correlation_limit) <= 0
    demo_mode = "full" if full else "moment"

    pool = await ensure_pool(settings)
    tables_meta: List[Dict[str, Any]] = []
    snapshot_at: Optional[str] = None
    async with pool.acquire() as conn:
        present = {
            r["tablename"]
            for r in await conn.fetch(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
            )
        }
        if full:
            export_tables = tuple(t for t in SNAPSHOT_TABLE_ORDER if t in present)
        else:
            export_tables = tuple(
                t
                for t in SNAPSHOT_TABLE_ORDER
                if t in FULL_EXPORT_TABLES or t in LIMITED_EXPORT_TABLES
            )
        for table in export_tables:
            if table not in present:
                continue
            if table == "tsoc_records" and not unlimited_records:
                rows = await conn.fetch(
                    "SELECT * FROM tsoc_records ORDER BY id DESC LIMIT $1",
                    int(record_limit),
                )
                rows = list(reversed(rows))
            elif table == "graph_findings" and not unlimited_findings:
                rows = await conn.fetch(
                    "SELECT * FROM graph_findings ORDER BY created_at DESC, id DESC LIMIT $1",
                    int(correlation_limit),
                )
                rows = list(reversed(rows))
            else:
                rows = await conn.fetch(f'SELECT * FROM "{table}" ORDER BY 1')
            if not rows:
                continue
            if table == "tsoc_records":
                latest = rows[-1]["created_at"]
                if isinstance(latest, datetime):
                    snapshot_at = latest.isoformat()
            payload = [_serialize_row(r) for r in rows]
            out_file = f"{table}.json"
            (target / out_file).write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            tables_meta.append({"name": table, "rows": len(payload), "file": out_file})

        for stale in SNAPSHOT_TABLE_ORDER:
            if stale in export_tables:
                continue
            stale_path = target / f"{stale}.json"
            if stale_path.is_file():
                stale_path.unlink()

    manifest = {
        "version": 2,
        "demo_mode": demo_mode,
        "record_limit": None if unlimited_records else int(record_limit),
        "correlation_limit": None if unlimited_findings else int(correlation_limit),
        "snapshot_at": snapshot_at,
        "tables": tables_meta,
    }
    (target / MANIFEST_FILE).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info(
        "postgres_snapshot exported %s demo (%d tables) to %s",
        demo_mode,
        len(tables_meta),
        target,
    )
    return target


async def _reset_serial_sequences(conn: Any) -> None:
    for table, column in (
        ("tsoc_records", "id"),
        ("tsoc_chat_messages", "message_id"),
    ):
        seq = await conn.fetchval(
            "SELECT pg_get_serial_sequence($1, $2)",
            table,
            column,
        )
        if not seq:
            continue
        await conn.execute(
            f"SELECT setval($1::regclass, COALESCE((SELECT MAX({column}) FROM {table}), 1), true)",
            seq,
        )


async def _connect_for_restore(settings: Settings) -> Any:
    import asyncpg

    from services.splunk_json_store.pg import _init_pg_connection

    dsn = (settings.tsoc_postgres_dsn or "").strip()
    if not dsn:
        raise ValueError("TSOC_POSTGRES_DSN is not configured")
    conn = await asyncpg.connect(dsn=dsn, timeout=30)
    await _init_pg_connection(conn)
    return conn


async def apply_postgres_demo_bundle(
    settings: Settings,
    *,
    demo_data_dir: Optional[Path] = None,
    allow_reseed: bool = False,
) -> bool:
    """Load bundled moment demo when empty or incomplete (install/setup)."""
    snap_dir = resolve_snapshot_dir(demo_data_dir)
    manifest_path = snap_dir / MANIFEST_FILE
    if not manifest_path.is_file():
        return False

    conn = await _connect_for_restore(settings)
    try:
        # Self-contained on a brand-new server DB: create tables before any
        # COUNT(*) check, so restore never trips on missing relations.
        await ensure_snapshot_schema(conn)
        needs = await _demo_bundle_needs_load(conn, manifest_path)
        if not needs:
            logger.info("postgres_snapshot already satisfies manifest — skip")
            return True
        if not await _inventory_empty(conn) and allow_reseed:
            await _truncate_demo_snapshot_tables(conn)
        elif not await _inventory_empty(conn):
            return False
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        table_files = {t["name"]: t["file"] for t in manifest.get("tables", [])}
        await _restore_into_conn(conn, table_files, snap_dir)
        return True
    finally:
        await conn.close()


async def restore_postgres_snapshot_if_empty(settings: Settings) -> bool:
    """Load snapshot when inventory tables are empty and manifest exists."""
    return await apply_postgres_demo_bundle(settings, allow_reseed=False)


async def _restore_into_conn(
    conn: Any,
    table_files: Dict[str, str],
    snap_dir: Path,
) -> None:
    await ensure_snapshot_schema(conn)
    for table in SNAPSHOT_TABLE_ORDER:
        filename = table_files.get(table)
        if not filename:
            continue
        path = snap_dir / filename
        if not path.is_file():
            continue
        rows: List[Dict[str, Any]] = json.loads(path.read_text(encoding="utf-8"))
        if not rows:
            continue
        columns = list(rows[0].keys())
        placeholders = ", ".join(f"${i + 1}" for i in range(len(columns)))
        col_list = ", ".join(columns)
        sql = f'INSERT INTO "{table}" ({col_list}) VALUES ({placeholders})'
        records = [
            tuple(_prepare_bind(col, row.get(col), table=table) for col in columns)
            for row in rows
        ]
        await conn.executemany(sql, records)
        logger.info("postgres_snapshot restored %s rows=%d", table, len(rows))

    await _reset_serial_sequences(conn)
    logger.info("postgres_snapshot restore complete from %s", snap_dir)
