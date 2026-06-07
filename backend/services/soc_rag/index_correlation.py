"""Index graph correlation findings and Neo4j alerts into SOC RAG."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

from config import Settings

from .compact_correlation import (
    DOC_TYPE_ALERT,
    DOC_TYPE_FINDING,
    DOC_TYPE_PATH,
    compact_attack_path_document,
    compact_finding_document,
    compact_graph_alert_document,
)
from .pg_store import upsert_rag_document

logger = logging.getLogger(__name__)

_CORRELATION_DIR = Path(__file__).resolve().parents[3] / "correlation"

_ALERTS_WITH_ENTITIES_QUERY = """
MATCH (a:Alert)
OPTIONAL MATCH (a)-[:RELATED_TO]->(e)
WITH a, collect(DISTINCT e.primary_identifier) AS entities
RETURN properties(a) AS props, entities
ORDER BY a.timestamp DESC
LIMIT $limit
"""

_CAUSED_PATHS_QUERY = """
MATCH (a1:Alert)-[c:CAUSED]->(a2:Alert)
RETURN a1.alert_row_id AS from_id,
       a2.alert_row_id AS to_id,
       properties(c) AS rel
LIMIT $limit
"""


def _ensure_correlation_path() -> None:
    path = str(_CORRELATION_DIR)
    if path not in sys.path:
        sys.path.insert(0, path)


async def index_correlation_catalog(
    settings: Settings,
    *,
    limit_findings: int = 100,
    limit_alerts: int = 400,
    limit_paths: int = 150,
    dry_run: bool = False,
) -> Dict[str, int]:
    """
    Index correlation Postgres findings + Neo4j alert graph into RAG.

    Requires TSOC_CORRELATION_ENABLED and working Neo4j/Postgres pools.
    """
    counts: Dict[str, int] = {
        DOC_TYPE_FINDING: 0,
        DOC_TYPE_ALERT: 0,
        DOC_TYPE_PATH: 0,
        "errors": 0,
    }
    if not settings.tsoc_correlation_enabled:
        logger.info("correlation RAG index skipped: disabled")
        return counts
    if not (settings.tsoc_postgres_dsn or "").strip():
        return counts

    _ensure_correlation_path()
    try:
        from graph_core.neo4j_driver import run_read_query, verify_connectivity
        from graph_core.postgres_pool import init_pool
        from graph_crud.findings import get_finding, list_findings
    except ImportError as exc:
        logger.warning("correlation RAG import failed: %s", exc)
        counts["errors"] += 1
        return counts

    await init_pool(settings)
    try:
        from graph_crud.schema import ensure_graph_schema

        await ensure_graph_schema(settings)
    except Exception as exc:
        logger.warning("correlation graph schema ensure failed: %s", exc)
        counts["errors"] += 1
        return counts

    neo4j_ok = await verify_connectivity(settings)
    if not neo4j_ok:
        logger.warning("correlation RAG: Neo4j unreachable — indexing findings only")

    # Postgres graph_findings
    try:
        page = await list_findings(limit=limit_findings, offset=0, finding_type=None)
        for item in page.items:
            try:
                detail = await get_finding(item.id)
                if detail is None:
                    continue
                doc = compact_finding_document(
                    finding_id=detail.id,
                    display_id=detail.display_id,
                    finding_type=detail.finding_type,
                    title=detail.title,
                    summary=detail.summary,
                    risk_score=detail.risk_score,
                    ticket_status=detail.ticket_status,
                    owner=detail.owner,
                    details=detail.details,
                )
                if dry_run:
                    counts[DOC_TYPE_FINDING] += 1
                else:
                    await upsert_rag_document(settings, doc)
                    counts[DOC_TYPE_FINDING] += 1
            except Exception as exc:
                logger.warning("correlation finding index failed id=%s: %s", item.id, exc)
                counts["errors"] += 1
    except Exception as exc:
        logger.warning("correlation findings list failed: %s", exc)
        counts["errors"] += 1

    if neo4j_ok:
        await _index_neo4j_alerts(
            settings,
            run_read_query,
            limit_alerts=limit_alerts,
            limit_paths=limit_paths,
            counts=counts,
            dry_run=dry_run,
        )

    logger.info("correlation RAG index done counts=%s", counts)
    return counts


async def _index_neo4j_alerts(
    settings: Settings,
    run_read_query: Any,
    *,
    limit_alerts: int,
    limit_paths: int,
    counts: Dict[str, int],
    dry_run: bool,
) -> None:
    try:
        rows = await run_read_query(
            _ALERTS_WITH_ENTITIES_QUERY,
            {"limit": max(1, limit_alerts)},
        )
        for row in rows:
            props = row.get("props") or {}
            if not isinstance(props, dict):
                continue
            alert_row_id = str(props.get("alert_row_id") or "").strip()
            if not alert_row_id:
                continue
            entities = row.get("entities") or []
            try:
                doc = compact_graph_alert_document(
                    alert_row_id=alert_row_id,
                    props=props,
                    related_entities=list(entities) if isinstance(entities, list) else [],
                )
                if dry_run:
                    counts[DOC_TYPE_ALERT] += 1
                else:
                    await upsert_rag_document(settings, doc)
                    counts[DOC_TYPE_ALERT] += 1
            except Exception as exc:
                logger.warning("correlation alert index failed id=%s: %s", alert_row_id, exc)
                counts["errors"] += 1
    except Exception as exc:
        logger.warning("correlation neo4j alerts query failed: %s", exc)
        counts["errors"] += 1

    try:
        path_rows = await run_read_query(
            _CAUSED_PATHS_QUERY,
            {"limit": max(1, limit_paths)},
        )
        for row in path_rows:
            from_id = str(row.get("from_id") or "").strip()
            to_id = str(row.get("to_id") or "").strip()
            if not from_id or not to_id:
                continue
            rel = row.get("rel") if isinstance(row.get("rel"), dict) else {}
            try:
                doc = compact_attack_path_document(
                    from_alert_id=from_id,
                    to_alert_id=to_id,
                    narrative=str(rel.get("narrative") or "") or None,
                    time_delta_seconds=rel.get("time_delta_seconds"),
                )
                if dry_run:
                    counts[DOC_TYPE_PATH] += 1
                else:
                    await upsert_rag_document(settings, doc)
                    counts[DOC_TYPE_PATH] += 1
            except Exception as exc:
                logger.warning("correlation path index failed %s->%s: %s", from_id, to_id, exc)
                counts["errors"] += 1
    except Exception as exc:
        logger.warning("correlation neo4j paths query failed: %s", exc)
        counts["errors"] += 1
