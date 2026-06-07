from __future__ import annotations

import logging
from typing import Any

from graph_core.neo4j_driver import run_write_query

logger = logging.getLogger("correlation.discovery")

_SYNC_INCIDENT_QUERY = """
MERGE (inc:Incident {incident_id: $incident_id})
SET inc.title = $title,
    inc.status = coalesce(inc.status, 'open'),
    inc.created_at = coalesce(inc.created_at, datetime())

WITH inc
UNWIND $alert_row_ids AS aid
MATCH (a:Alert {alert_row_id: aid})
MERGE (a)-[:PART_OF_INCIDENT]->(inc)
RETURN count(DISTINCT a) AS linked
"""

_ENSURE_CAUSED_CHAIN_QUERY = """
MATCH (inc:Incident {incident_id: $incident_id})<-[:PART_OF_INCIDENT]-(a:Alert)
WITH a ORDER BY a.timestamp ASC
WITH collect(a) AS alerts
WHERE size(alerts) >= 2
UNWIND range(0, size(alerts) - 2) AS i
WITH alerts[i] AS prev, alerts[i + 1] AS curr
MERGE (prev)-[r:CAUSED]->(curr)
SET r.confidence = coalesce(r.confidence, 'chronological_sequence'),
    r.time_delta_seconds = CASE
        WHEN prev.timestamp IS NOT NULL AND curr.timestamp IS NOT NULL
        THEN toInteger(duration.between(prev.timestamp, curr.timestamp).seconds)
        ELSE r.time_delta_seconds
    END
RETURN count(*) AS edges
"""


async def sync_finding_incident_to_neo4j(
    *,
    incident_id: str,
    title: str,
    alert_row_ids: list[str],
) -> int:
    """Link existing Alert nodes to a finding incident in Neo4j for Graph Explorer."""
    ids = [str(aid) for aid in alert_row_ids if aid]
    if not incident_id or not ids:
        return 0

    rows = await run_write_query(
        _SYNC_INCIDENT_QUERY,
        {
            "incident_id": str(incident_id),
            "title": str(title or incident_id),
            "alert_row_ids": ids,
        },
    )
    linked = int((rows[0] or {}).get("linked") or 0) if rows else 0
    if linked == 0:
        logger.warning(
            "correlation step=neo4j_sync incident_id=%s linked=0 alert_row_ids=%s",
            incident_id,
            ids,
        )
        return 0

    try:
        caused_rows = await run_write_query(
            _ENSURE_CAUSED_CHAIN_QUERY,
            {"incident_id": str(incident_id)},
        )
        edges = int((caused_rows[0] or {}).get("edges") or 0) if caused_rows else 0
    except Exception as exc:
        logger.debug("correlation step=neo4j_caused_skip incident_id=%s error=%s", incident_id, exc)
        edges = 0

    logger.info(
        "correlation step=neo4j_sync incident_id=%s title=%r linked=%d caused_edges=%d alert_row_ids=%s",
        incident_id,
        title,
        linked,
        edges,
        ids,
    )
    return linked
