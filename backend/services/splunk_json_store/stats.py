"""PostgreSQL aggregations for dashboard overview."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Tuple

from config import Settings

from . import pg
from .pg import init_store, splunk_store_configured

logger = logging.getLogger(__name__)

async def _ensure_pool(settings: Settings) -> bool:
    if not splunk_store_configured(settings):
        return False
    if pg._PG_POOL is None:
        await init_store(settings)
    return pg._PG_POOL is not None


async def fetch_record_counts_by_type(settings: Settings) -> List[Dict[str, Any]]:
    if not await _ensure_pool(settings):
        return []
    query = """
        SELECT tsoc_record_type AS type, COUNT(*)::int AS count
        FROM tsoc_records
        GROUP BY tsoc_record_type
        ORDER BY count DESC, type ASC
    """
    async with pg._PG_POOL.acquire() as conn:
        rows = await conn.fetch(query)
    return [{"type": row["type"], "count": int(row["count"])} for row in rows]


async def fetch_total_records(settings: Settings) -> int:
    if not await _ensure_pool(settings):
        return 0
    async with pg._PG_POOL.acquire() as conn:
        val = await conn.fetchval("SELECT COUNT(*)::int FROM tsoc_records")
    return int(val or 0)


async def fetch_records_last_24h(settings: Settings) -> int:
    if not await _ensure_pool(settings):
        return 0
    async with pg._PG_POOL.acquire() as conn:
        val = await conn.fetchval(
            """
            SELECT COUNT(*)::int FROM tsoc_records
            WHERE created_at >= NOW() - INTERVAL '24 hours'
            """
        )
    return int(val or 0)


async def fetch_analyses_last_24h(settings: Settings) -> int:
    if not await _ensure_pool(settings):
        return 0
    async with pg._PG_POOL.acquire() as conn:
        val = await conn.fetchval(
            """
            SELECT COUNT(*)::int FROM tsoc_records
            WHERE created_at >= NOW() - INTERVAL '24 hours'
              AND tsoc_record_type IN ('soc_analysis', 'observability_analysis')
            """
        )
    return int(val or 0)


async def fetch_activity_by_day(
    settings: Settings,
    *,
    days: int = 14,
) -> List[Dict[str, Any]]:
    """Daily activity buckets from PostgreSQL (zeros only for days with no rows in range)."""
    if not await _ensure_pool(settings):
        return []
    query = """
        WITH day_series AS (
            SELECT d::date AS day
            FROM generate_series(
                CURRENT_DATE - ($1::int - 1),
                CURRENT_DATE,
                INTERVAL '1 day'
            ) AS d
        ),
        daily AS (
            SELECT
                (created_at AT TIME ZONE 'UTC')::date AS day,
                tsoc_record_type,
                COUNT(*)::int AS cnt
            FROM tsoc_records
            WHERE created_at >= (CURRENT_DATE - ($1::int - 1))::timestamptz
            GROUP BY 1, 2
        ),
        correlation_daily AS (
            SELECT
                (created_at AT TIME ZONE 'UTC')::date AS day,
                COUNT(*)::int AS cnt
            FROM graph_findings
            WHERE created_at >= (CURRENT_DATE - ($1::int - 1))::timestamptz
            GROUP BY 1
        )
        SELECT
            ds.day,
            COALESCE(SUM(CASE
                WHEN d.tsoc_record_type = 'soc_analysis' THEN d.cnt END), 0)::int AS security,
            COALESCE(SUM(CASE
                WHEN d.tsoc_record_type = 'observability_analysis' THEN d.cnt END), 0)::int AS observability,
            COALESCE(MAX(c.cnt), 0)::int AS correlation,
            COALESCE(SUM(CASE
                WHEN d.tsoc_record_type IS NOT NULL
                 AND d.tsoc_record_type NOT IN ('soc_analysis', 'observability_analysis')
                 THEN d.cnt END), 0)::int AS other
        FROM day_series ds
        LEFT JOIN daily d ON d.day = ds.day
        LEFT JOIN correlation_daily c ON c.day = ds.day
        GROUP BY ds.day
        ORDER BY ds.day ASC
    """
    try:
        async with pg._PG_POOL.acquire() as conn:
            rows = await conn.fetch(query, days)
    except Exception:
        fallback_query = """
            WITH day_series AS (
                SELECT d::date AS day
                FROM generate_series(
                    CURRENT_DATE - ($1::int - 1),
                    CURRENT_DATE,
                    INTERVAL '1 day'
                ) AS d
            ),
            daily AS (
                SELECT
                    (created_at AT TIME ZONE 'UTC')::date AS day,
                    tsoc_record_type,
                    COUNT(*)::int AS cnt
                FROM tsoc_records
                WHERE created_at >= (CURRENT_DATE - ($1::int - 1))::timestamptz
                GROUP BY 1, 2
            )
            SELECT
                ds.day,
                COALESCE(SUM(CASE
                    WHEN d.tsoc_record_type = 'soc_analysis' THEN d.cnt END), 0)::int AS security,
                COALESCE(SUM(CASE
                    WHEN d.tsoc_record_type = 'observability_analysis' THEN d.cnt END), 0)::int AS observability,
                0::int AS correlation,
                COALESCE(SUM(CASE
                    WHEN d.tsoc_record_type IS NOT NULL
                     AND d.tsoc_record_type NOT IN ('soc_analysis', 'observability_analysis')
                     THEN d.cnt END), 0)::int AS other
            FROM day_series ds
            LEFT JOIN daily d ON d.day = ds.day
            GROUP BY ds.day
            ORDER BY ds.day ASC
        """
        async with pg._PG_POOL.acquire() as conn:
            rows = await conn.fetch(fallback_query, days)

    timeline: List[Dict[str, Any]] = []
    for row in rows:
        day_val = row["day"]
        if isinstance(day_val, datetime):
            day_key = day_val.date()
        else:
            day_key = day_val
        timeline.append(
            {
                "date": day_key.isoformat(),
                "security": int(row["security"]),
                "observability": int(row["observability"]),
                "correlation": int(row["correlation"]),
                "other": int(row["other"]),
            }
        )
    return timeline


async def fetch_inventory_counts(settings: Settings) -> Tuple[int, int]:
    if not await _ensure_pool(settings):
        return 0, 0
    async with pg._PG_POOL.acquire() as conn:
        users = await conn.fetchval("SELECT COUNT(*)::int FROM tsoc_users")
        assets = await conn.fetchval("SELECT COUNT(*)::int FROM tsoc_assets")
    return int(users or 0), int(assets or 0)


async def fetch_runbook_ops(settings: Settings) -> Dict[str, Any]:
    """One-roundtrip rollup for ThinkingSOC Lite, reuse, Autopilot, and SOC Chat."""
    if not await _ensure_pool(settings):
        return {}
    query = """
        WITH latest_drafts AS (
            SELECT DISTINCT ON (payload->>'source_record_id')
                payload,
                search_name
            FROM tsoc_records
            WHERE tsoc_record_type = 'verified_runbook_draft'
            ORDER BY
                payload->>'source_record_id',
                CASE WHEN payload->>'revision' ~ '^[0-9]+$'
                    THEN (payload->>'revision')::int ELSE 0 END DESC,
                id DESC
        ),
        latest_approvals AS (
            SELECT DISTINCT ON (
                payload->>'source_record_id',
                payload->>'runbook_id'
            ) payload
            FROM tsoc_records
            WHERE tsoc_record_type = 'verified_runbook_approval'
            ORDER BY
                payload->>'source_record_id',
                payload->>'runbook_id',
                id DESC
        ),
        draft_rollup AS (
            SELECT
                COUNT(*)::int AS latest_runbooks,
                COUNT(*) FILTER (
                    WHERE d.payload->>'status' = 'SOURCE_VERIFIED'
                )::int AS source_verified,
                COUNT(*) FILTER (
                    WHERE d.payload->>'status' = 'SOURCE_VERIFIED'
                      AND a.payload->>'decision' = 'approve'
                )::int AS human_approved,
                COUNT(DISTINCT d.search_name) FILTER (
                    WHERE d.payload->>'status' = 'SOURCE_VERIFIED'
                      AND a.payload->>'decision' = 'approve'
                )::int AS reusable_alert_names
            FROM latest_drafts d
            LEFT JOIN latest_approvals a
              ON a.payload->>'source_record_id' = d.payload->>'source_record_id'
             AND a.payload->>'runbook_id' = d.payload->>'runbook_id'
        ),
        run_rollup AS (
            SELECT
                COUNT(*)::int AS executions,
                COUNT(*) FILTER (WHERE payload->>'status' = 'REUSED')::int AS reused,
                COUNT(*) FILTER (WHERE payload->>'status' = 'NO_EVIDENCE')::int AS no_evidence,
                COUNT(*) FILTER (WHERE payload->>'status' = 'FAILED')::int AS failed,
                COALESCE(SUM(CASE
                    WHEN payload->>'total_evidence_rows' ~ '^[0-9]+$'
                    THEN (payload->>'total_evidence_rows')::int ELSE 0 END), 0)::int
                    AS evidence_rows,
                COALESCE(SUM(CASE
                    WHEN payload->>'estimated_minutes_saved' ~ '^[0-9]+([.][0-9]+)?$'
                    THEN (payload->>'estimated_minutes_saved')::numeric ELSE 0 END), 0)::float
                    AS estimated_minutes_saved
            FROM tsoc_records
            WHERE tsoc_record_type = 'verified_runbook_run'
        ),
        artifact_rollup AS (
            SELECT
                COUNT(*) FILTER (
                    WHERE tsoc_record_type = 'verified_runbook_shadow_run'
                )::int AS shadow_runs,
                COUNT(*) FILTER (
                    WHERE tsoc_record_type = 'verified_runbook_response_preview'
                )::int AS response_previews,
                COUNT(*) FILTER (
                    WHERE tsoc_record_type = 'verified_runbook_autopilot_session'
                )::int AS autopilot_sessions,
                COUNT(*) FILTER (
                    WHERE tsoc_record_type = 'verified_runbook_autopilot_session'
                      AND payload->>'status' = 'COMPLETED'
                )::int AS autopilot_completed
            FROM tsoc_records
        )
        SELECT
            d.*,
            r.*,
            a.*,
            (SELECT COUNT(*)::int FROM tsoc_chat_conversations) AS chat_conversations,
            (SELECT COUNT(*)::int FROM tsoc_chat_messages) AS chat_messages
        FROM draft_rollup d
        CROSS JOIN run_rollup r
        CROSS JOIN artifact_rollup a
    """
    try:
        async with pg._PG_POOL.acquire() as conn:
            row = await conn.fetchrow(query)
    except Exception as exc:
        # Dashboard availability must not depend on optional Chat/ThinkingSOC Lite tables
        # while an older installation is still being migrated.
        logger.warning("dashboard Runbook operations rollup unavailable: %s", exc)
        return {}
    return dict(row) if row else {}
