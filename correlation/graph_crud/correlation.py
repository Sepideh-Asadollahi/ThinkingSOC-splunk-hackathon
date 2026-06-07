from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from graph_core.entity_taxonomy import (
    anchor_entities_from_identifiers,
    is_indicator_only_alert,
)
from graph_core.neo4j_driver import run_read_query
from graph_core.neo4j_sanitize import sanitize_neo4j_value
from graph_pipelines.correlation_logging import log_step
from graph_schemas.exploration import CorrelatedAlert, CorrelateRequest, CorrelateResponse


def _format_timestamp(value: Any) -> str:
    sanitized = sanitize_neo4j_value(value)
    if sanitized is None:
        return ""
    return str(sanitized)


_CORRELATE_QUERY_TEMPLATE = """
UNWIND $entity_identifiers AS entityId
MATCH (startNode)
WHERE (startNode:IOC OR startNode:Asset OR startNode:Identity)
  AND startNode.primary_identifier = entityId

MATCH path = (startNode)-[*1..{depth}]-(alertNode:Alert)
WHERE alertNode.alert_row_id <> $current_alert_row_id

WITH alertNode, COLLECT(DISTINCT startNode.primary_identifier) AS commonEntities

RETURN
    properties(alertNode) AS alert_properties,
    commonEntities AS entities_in_common
ORDER BY alertNode.timestamp DESC
LIMIT 50
"""

_HISTORICAL_INCIDENTS_QUERY = """
UNWIND $alert_ids AS new_alert_id
MATCH (newAlert:Alert {alert_row_id: new_alert_id})
MATCH (newAlert)--(entity)
WHERE NOT entity:Incident
  AND (entity:Identity OR entity:Asset OR entity:IOC)

MATCH (entity)--(oldAlert:Alert)
WHERE oldAlert.alert_row_id <> new_alert_id
MATCH (oldAlert)-[:PART_OF_INCIDENT]->(oldIncident:Incident)

WHERE oldIncident.created_at >= datetime($lookback_time_iso)

RETURN DISTINCT oldIncident.incident_id AS related_incident_id,
       count(DISTINCT entity) AS shared_entity_count
ORDER BY shared_entity_count DESC
LIMIT 5
"""


async def find_correlated_alerts(request: CorrelateRequest) -> CorrelateResponse:
    depth = max(1, min(4, request.depth))
    query = _CORRELATE_QUERY_TEMPLATE.format(depth=depth)
    rows = await run_read_query(
        query,
        {
            "entity_identifiers": request.entity_identifiers,
            "current_alert_row_id": request.current_alert_row_id,
        },
    )
    alerts: list[CorrelatedAlert] = []
    for row in rows:
        props = row.get("alert_properties") or {}
        alerts.append(
            CorrelatedAlert(
                alert_row_id=str(props.get("alert_row_id", "")),
                name=str(props.get("name", "")),
                status=str(props.get("status", "")),
                risk_score=int(props.get("risk_score") or 0),
                timestamp=_format_timestamp(props.get("timestamp")),
                entities_in_common=list(row.get("entities_in_common") or []),
            )
        )
    return CorrelateResponse(
        correlated_alerts=alerts,
        total_found=len(alerts),
        suggested_queries=[],
    )


async def find_historical_related_incidents(
    alert_ids: list[str],
    *,
    lookback_days: int = 7,
) -> list[dict[str, Any]]:
    if not alert_ids:
        return []
    lookback = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    lookback_iso = lookback.strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = await run_read_query(
        _HISTORICAL_INCIDENTS_QUERY,
        {"alert_ids": alert_ids, "lookback_time_iso": lookback_iso},
    )
    return [
        {
            "incident_id": row["related_incident_id"],
            "shared_entity_count": int(row["shared_entity_count"]),
        }
        for row in rows
    ]


_LOAD_ALERTS_QUERY = """
MATCH (a:Alert)
WHERE $lookback_iso IS NULL OR a.timestamp >= datetime($lookback_iso)
OPTIONAL MATCH (a)-[:RELATED_TO]->(e)
WHERE e:Identity OR e:Asset OR e:IOC
WITH a, collect(DISTINCT e.primary_identifier) AS entities
RETURN properties(a) AS props, entities
ORDER BY a.timestamp DESC
LIMIT $limit
"""

_EXPAND_CAMPAIGN_ALERTS_QUERY = """
UNWIND $campaign_entities AS entityId
MATCH (n)
WHERE (n:Identity OR n:Asset) AND n.primary_identifier = entityId
MATCH (n)<-[:RELATED_TO]-(a:Alert)
WHERE a.timestamp >= datetime($lookback_iso)
OPTIONAL MATCH (a)-[:RELATED_TO]->(e)
WHERE e:Identity OR e:Asset OR e:IOC
WITH DISTINCT a, collect(DISTINCT e.primary_identifier) AS entities
RETURN properties(a) AS props, entities
"""


def _alerts_from_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []
    for row in rows:
        props = dict(row.get("props") or {})
        props["entity_identifiers"] = [
            str(e) for e in (row.get("entities") or []) if e
        ]
        alerts.append(props)
    return alerts


def _campaign_entities_from_alerts(alerts: list[dict[str, Any]]) -> list[str]:
    entities: set[str] = set()
    for alert in alerts:
        entities.update(anchor_entities_from_identifiers(alert.get("entity_identifiers") or []))
    return sorted(entities)


def _alert_ts_sort_key(alert: dict[str, Any]) -> float:
    ts = alert.get("timestamp")
    if ts is None:
        return 0.0
    if hasattr(ts, "to_native"):
        ts = ts.to_native()
    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return ts.timestamp()
    if isinstance(ts, str):
        try:
            parsed = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            return parsed.timestamp()
        except ValueError:
            return 0.0
    return 0.0


def _cap_alert_pool(
    alerts: list[dict[str, Any]],
    limit: int,
    *,
    anchor: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Keep at most ``limit`` alerts, preferring anchor-linked rows over indicator-only rows."""
    if len(alerts) <= limit:
        return alerts

    anchor_ids = {str(a.get("alert_row_id")) for a in anchor if a.get("alert_row_id")}
    anchor_campaign = set(_campaign_entities_from_alerts(anchor))

    def priority(alert: dict[str, Any]) -> tuple[int, int, int, float]:
        campaign = anchor_entities_from_identifiers(alert.get("entity_identifiers") or [])
        return (
            1 if campaign & anchor_campaign else 0,
            1 if str(alert.get("alert_row_id")) in anchor_ids else 0,
            0 if is_indicator_only_alert(alert) else 1,
            _alert_ts_sort_key(alert),
        )

    kept = sorted(alerts, key=priority, reverse=True)[:limit]
    dropped = [
        str(a.get("alert_row_id"))
        for a in alerts
        if str(a.get("alert_row_id")) not in {str(k.get("alert_row_id")) for k in kept}
    ]
    log_step(
        "neo4j_load_cap",
        limit=limit,
        before_count=len(alerts),
        after_count=len(kept),
        kept_ids=[str(a.get("alert_row_id")) for a in kept],
        dropped_ids=dropped,
    )
    return _merge_alerts_by_id(kept)


def _merge_alerts_by_id(*groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for group in groups:
        for alert in group:
            aid = alert.get("alert_row_id")
            if aid:
                by_id[str(aid)] = alert
    return sorted(
        by_id.values(),
        key=lambda a: _format_timestamp(a.get("timestamp")),
        reverse=True,
    )


async def load_alerts_from_neo4j(
    *,
    limit: int = 50,
    lookback_days: int | None = 7,
) -> list[dict[str, Any]]:
    """Load recent alerts, then expand with same anchor-entity alerts in the lookback window.

    ``limit`` caps the initial newest-by-time fetch; expansion adds related in-window alerts
    that share Identity/Asset anchors and would otherwise be dropped when the graph has more
    alerts than ``limit``. The pool is then capped again, preferring anchor links over
    indicator-only rows.
    """
    lookback_iso: str | None = None
    if lookback_days is not None:
        lookback = datetime.now(timezone.utc) - timedelta(days=lookback_days)
        lookback_iso = lookback.strftime("%Y-%m-%dT%H:%M:%SZ")

    rows = await run_read_query(
        _LOAD_ALERTS_QUERY,
        {"limit": limit, "lookback_iso": lookback_iso},
    )
    alerts = _alerts_from_rows(rows)

    campaign_entities = _campaign_entities_from_alerts(alerts)
    if not campaign_entities or lookback_iso is None:
        return alerts

    extra_rows = await run_read_query(
        _EXPAND_CAMPAIGN_ALERTS_QUERY,
        {"campaign_entities": campaign_entities, "lookback_iso": lookback_iso},
    )
    expanded = _merge_alerts_by_id(alerts, _alerts_from_rows(extra_rows))
    return _cap_alert_pool(expanded, limit, anchor=alerts)
