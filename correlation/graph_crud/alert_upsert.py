from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from graph_core.neo4j_driver import run_write_query

logger = logging.getLogger(__name__)

_UPSERT_ALERT = """
MERGE (a:Alert {alert_row_id: $alert_row_id})
SET a.name = $name,
    a.sid = $sid,
    a.search_name = $search_name,
    a.status = $status,
    a.risk_score = $risk_score,
    a.timestamp = CASE
        WHEN $timestamp IS NULL OR $timestamp = '' THEN coalesce(a.timestamp, datetime())
        ELSE datetime($timestamp)
    END
RETURN a.alert_row_id AS alert_row_id
"""

_RELATE_ENTITY = """
MATCH (a:Alert {alert_row_id: $alert_row_id})
MERGE (e:{label} {{primary_identifier: $entity_id}})
SET e.name = coalesce(e.name, $display)
MERGE (a)-[:RELATED_TO]->(e)
"""


def _entity_label(entity_id: str) -> str | None:
    if entity_id.startswith("username:"):
        return "Identity"
    if entity_id.startswith("hostname:"):
        return "Asset"
    if entity_id.startswith(("ipv4:", "domain:")):
        return "IOC"
    return None


def _display_name(entity_id: str) -> str:
    return entity_id.split(":", 1)[-1] if ":" in entity_id else entity_id


def _parse_webhook_alert(payload: dict[str, Any]) -> dict[str, Any] | None:
    corr = payload.get("correlation")
    if not isinstance(corr, dict):
        return None
    alert_row_id = str(corr.get("alert_row_id") or "").strip()
    if not alert_row_id:
        return None

    name = str(payload.get("search_name") or corr.get("name") or alert_row_id)
    risk = int(corr.get("risk_score") or 0)
    status = str(corr.get("status") or "open").lower()
    timestamp = corr.get("timestamp")
    if not timestamp:
        norm = payload.get("normalized") or {}
        if isinstance(norm, dict):
            timestamp = norm.get("_time") or norm.get("timestamp")
        result = payload.get("result")
        if not timestamp and isinstance(result, dict):
            timestamp = result.get("_time")

    ts_str: str | None = None
    if isinstance(timestamp, datetime):
        ts = timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=timezone.utc)
        ts_str = ts.isoformat().replace("+00:00", "Z")
    elif timestamp:
        ts_str = str(timestamp)

    entities = [
        str(e) for e in (corr.get("entity_identifiers") or []) if e
    ]

    sid = str(payload.get("sid") or corr.get("sid") or "").strip()
    search_name = str(payload.get("search_name") or corr.get("search_name") or name).strip()

    return {
        "alert_row_id": alert_row_id,
        "name": name,
        "sid": sid,
        "search_name": search_name,
        "status": status,
        "risk_score": risk if risk > 0 else 55,
        "timestamp": ts_str,
        "entity_identifiers": entities,
    }


async def upsert_alert_from_webhook(payload: dict[str, Any]) -> bool:
    """MERGE Alert + entity nodes from Splunk webhook correlation block."""
    alert = _parse_webhook_alert(payload)
    if alert is None:
        return False

    await run_write_query(
        _UPSERT_ALERT,
        {
            "alert_row_id": alert["alert_row_id"],
            "name": alert["name"],
            "sid": alert.get("sid") or "",
            "search_name": alert.get("search_name") or alert["name"],
            "status": alert["status"],
            "risk_score": alert["risk_score"],
            "timestamp": alert.get("timestamp"),
        },
    )

    for entity_id in alert["entity_identifiers"]:
        label = _entity_label(entity_id)
        if not label:
            continue
        query = _RELATE_ENTITY.format(label=label)
        await run_write_query(
            query,
            {
                "alert_row_id": alert["alert_row_id"],
                "entity_id": entity_id,
                "display": _display_name(entity_id),
            },
        )

    logger.info(
        "neo4j upsert alert_row_id=%s entities=%d",
        alert["alert_row_id"],
        len(alert["entity_identifiers"]),
    )
    return True
