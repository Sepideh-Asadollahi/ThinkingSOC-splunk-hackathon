from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID, uuid4

from graph_core.postgres_pool import get_pool
from graph_schemas.finding import (
    GraphFindingDetails,
    GraphFindingSummary,
    PaginatedGraphFindingsResponse,
    PatchFindingTicketRequest,
)


def _parse_details(raw: Any) -> dict[str, Any]:
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        return json.loads(raw)
    return dict(raw)


def _row_to_summary(row: Any) -> GraphFindingSummary:
    return GraphFindingSummary(
        id=str(row["id"]),
        display_id=row["display_id"] or "",
        finding_type=row["finding_type"] or "",
        title=row["title"] or "",
        summary=row["summary"] or "",
        risk_score=int(row["risk_score"] or 0),
        created_at=row["created_at"],
        ticket_status=row["ticket_status"] or "open",
        owner=row["owner"] or "unassigned",
        updated_at=row.get("updated_at"),
        agent_validation_status=row.get("agent_validation_status"),
    )


def _row_to_details(row: Any) -> GraphFindingDetails:
    summary = _row_to_summary(row)
    return GraphFindingDetails(
        **summary.model_dump(),
        details=_parse_details(row["details"]),
        status=row.get("status"),
    )


async def list_findings(
    *,
    limit: int = 20,
    offset: int = 0,
    finding_type: Optional[str] = "smart_attack_discovery",
    exclude_finding_type: Optional[str] = None,
) -> PaginatedGraphFindingsResponse:
    pool = get_pool()
    clauses: list[str] = []
    params: list[Any] = []
    idx = 1
    if finding_type:
        clauses.append(f"finding_type = ${idx}")
        params.append(finding_type)
        idx += 1
    if exclude_finding_type:
        clauses.append(f"finding_type <> ${idx}")
        params.append(exclude_finding_type)
        idx += 1
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    count_sql = f"SELECT COUNT(*) FROM graph_findings {where}"
    list_sql = f"""
        SELECT id, display_id, finding_type, title, summary, risk_score,
               created_at, ticket_status, owner, updated_at, agent_validation_status, status
        FROM graph_findings
        {where}
        ORDER BY risk_score DESC, created_at DESC
        LIMIT ${idx} OFFSET ${idx + 1}
    """
    async with pool.acquire() as conn:
        total = await conn.fetchval(count_sql, *params)
        rows = await conn.fetch(list_sql, *params, limit, offset)
    items = [_row_to_summary(r) for r in rows]
    return PaginatedGraphFindingsResponse(
        items=items,
        total=int(total or 0),
        limit=limit,
        offset=offset,
    )


async def get_finding(finding_id: str) -> Optional[GraphFindingDetails]:
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, display_id, finding_type, title, summary, details, risk_score,
                   created_at, ticket_status, owner, updated_at, agent_validation_status, status
            FROM graph_findings WHERE id = $1::uuid
            """,
            finding_id,
        )
    if row is None:
        return None
    return _row_to_details(row)


async def patch_finding_ticket(
    finding_id: str,
    body: PatchFindingTicketRequest,
) -> Optional[GraphFindingDetails]:
    pool = get_pool()
    existing = await get_finding(finding_id)
    if existing is None:
        return None

    updates: list[str] = ["updated_at = NOW()"]
    params: list[Any] = []
    idx = 1
    if body.ticket_status is not None:
        updates.append(f"ticket_status = ${idx}")
        params.append(body.ticket_status)
        idx += 1
    if body.assigned_to_user_id is not None:
        updates.append(f"owner = ${idx}")
        params.append(body.assigned_to_user_id or "unassigned")
        idx += 1
    if body.new_note:
        details = dict(existing.details or {})
        notes = list(details.get("ticket_notes") or [])
        notes.append(
            {
                "text": body.new_note,
                "created_at": datetime.now(timezone.utc)
                .isoformat()
                .replace("+00:00", "Z"),
            }
        )
        details["ticket_notes"] = notes
        updates.append(f"details = ${idx}::jsonb")
        params.append(json.dumps(details))
        idx += 1
    if not params:
        return existing
    params.append(finding_id)
    sql = f"""
        UPDATE graph_findings SET {", ".join(updates)}
        WHERE id = ${idx}::uuid
        RETURNING id, display_id, finding_type, title, summary, details, risk_score,
                  created_at, ticket_status, owner, updated_at, agent_validation_status, status
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(sql, *params)
    if row is None:
        return None
    return _row_to_details(row)


async def insert_finding(
    *,
    title: str,
    summary: str,
    details: dict[str, Any],
    risk_score: int,
    finding_type: str = "smart_attack_discovery",
    display_id: Optional[str] = None,
    content_hash: Optional[str] = None,
) -> str:
    finding_id = str(uuid4())
    pool = get_pool()
    async with pool.acquire() as conn:
        count = await conn.fetchval("SELECT COUNT(*) FROM graph_findings")
        disp = display_id or f"GF-{int(count or 0) + 1:04d}"
        await conn.execute(
            """
            INSERT INTO graph_findings (
                id, finding_type, title, summary, details, risk_score,
                status, ticket_status, owner, display_id, created_at, updated_at, content_hash
            ) VALUES (
                $1::uuid, $2, $3, $4, $5::jsonb, $6,
                'open', 'open', 'unassigned', $7, NOW(), NOW(), $8
            )
            """,
            finding_id,
            finding_type,
            title,
            summary,
            json.dumps(details),
            risk_score,
            disp,
            content_hash,
        )
    return finding_id


async def find_by_content_hash(content_hash: str) -> list[str]:
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id::text FROM graph_findings WHERE content_hash = $1",
            content_hash,
        )
    return [r["id"] for r in rows]
