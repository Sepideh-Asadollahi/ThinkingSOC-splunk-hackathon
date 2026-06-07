from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from graph_core.neo4j_driver import run_read_query
from graph_core.neo4j_sanitize import sanitize_neo4j_value
from graph_crud.findings import get_finding
from graph_schemas.exploration import (
    AttackTreeResponse,
    GraphEdge,
    GraphExplorationResponse,
    GraphNode,
    GraphTreeNode,
    HighlightInfo,
)

_INCIDENT_ALERTS_QUERY = """
MATCH (inc:Incident {incident_id: $incident_id})<-[:PART_OF_INCIDENT]-(a:Alert)
WHERE size($alert_ids) = 0 OR a.alert_row_id IN $alert_ids
RETURN
    elementId(a) AS nid,
    labels(a) AS nlabels,
    properties(a) AS nprops
ORDER BY a.timestamp ASC
"""

_ALERTS_BY_ID_QUERY = """
MATCH (a:Alert)
WHERE a.alert_row_id IN $alert_ids
RETURN
    elementId(a) AS nid,
    labels(a) AS nlabels,
    properties(a) AS nprops
ORDER BY a.timestamp ASC
"""

_ALERTS_SUBGRAPH_QUERY = """
MATCH (a:Alert)
WHERE a.alert_row_id IN $alert_ids
WITH collect(DISTINCT a) AS alerts
UNWIND alerts AS node
WITH collect(DISTINCT node) AS nodes
UNWIND nodes AS node
OPTIONAL MATCH (node)-[r]-(m)
WHERE m IN nodes OR (m:Identity OR m:Asset OR m:IOC)
RETURN
    elementId(node) AS nid,
    labels(node) AS nlabels,
    properties(node) AS nprops,
    elementId(r) AS rid,
    type(r) AS rtype,
    elementId(startNode(r)) AS from_id,
    elementId(endNode(r)) AS to_id,
    properties(r) AS rprops
"""

_INCIDENT_SUBGRAPH_QUERY = """
MATCH (inc:Incident {incident_id: $incident_id})<-[:PART_OF_INCIDENT]-(a:Alert)
WHERE size($alert_ids) = 0 OR a.alert_row_id IN $alert_ids
WITH inc, collect(DISTINCT a) AS alerts
WITH [inc] + alerts AS seedNodes
UNWIND seedNodes AS node
WITH collect(DISTINCT node) AS nodes
UNWIND nodes AS node
OPTIONAL MATCH (node)-[r]-(m)
WHERE m IN nodes AND elementId(node) <= elementId(m)
RETURN
    elementId(node) AS nid,
    labels(node) AS nlabels,
    properties(node) AS nprops,
    elementId(r) AS rid,
    type(r) AS rtype,
    elementId(startNode(r)) AS from_id,
    elementId(endNode(r)) AS to_id,
    properties(r) AS rprops
"""


def _label_for_node(labels: list[str], props: dict[str, Any]) -> str:
    if "Alert" in labels:
        return str(props.get("name") or props.get("alert_row_id") or "Alert")
    if "Asset" in labels:
        return str(props.get("name") or props.get("primary_identifier") or "Asset")
    if "Identity" in labels:
        return str(props.get("name") or props.get("primary_identifier") or "Identity")
    if "IOC" in labels:
        return str(props.get("value") or props.get("primary_identifier") or "IOC")
    if "Incident" in labels:
        return str(props.get("title") or props.get("incident_id") or "Incident")
    return str(props.get("name") or props.get("primary_identifier") or "Node")


def _merge_subgraph_rows(
    caused_nodes: list[GraphNode],
    caused_edges: list[GraphEdge],
    subgraph_rows: list[dict[str, Any]],
) -> tuple[list[GraphNode], list[GraphEdge]]:
    nodes_by_id = {n.id: n for n in caused_nodes}
    edges_by_id = {e.id: e for e in caused_edges}

    for row in subgraph_rows:
        nid = row.get("nid")
        if nid is not None:
            sid = str(nid)
            if sid not in nodes_by_id:
                labels = row.get("nlabels") or []
                props = sanitize_neo4j_value(row.get("nprops") or {})
                group = list(labels) if labels else ["Node"]
                nodes_by_id[sid] = GraphNode(
                    id=sid,
                    label=_label_for_node(group, props),
                    group=group,
                    properties=props,
                )
        rid = row.get("rid")
        if rid is not None:
            eid = str(rid)
            if eid not in edges_by_id:
                edges_by_id[eid] = GraphEdge(
                    id=eid,
                    **{"from": str(row["from_id"])},
                    to=str(row["to_id"]),
                    label=str(row.get("rtype") or "RELATED"),
                    properties=sanitize_neo4j_value(row.get("rprops") or {}),
                )

    return list(nodes_by_id.values()), list(edges_by_id.values())


def _dedupe_parallel_caused_edges(edges: list[GraphEdge]) -> list[GraphEdge]:
    """One CAUSED edge per alert pair (synthetic seq + Neo4j merge overlap)."""
    by_pair: dict[tuple[str, str], GraphEdge] = {}
    rest: list[GraphEdge] = []
    for edge in edges:
        if edge.label != "CAUSED":
            rest.append(edge)
            continue
        key = (edge.from_, edge.to)
        existing = by_pair.get(key)
        if existing is None:
            by_pair[key] = edge
            continue
        prev_props = dict(existing.properties or {})
        next_props = dict(edge.properties or {})
        narrative = next_props.get("narrative") or prev_props.get("narrative")
        merged = {**prev_props, **next_props}
        if narrative:
            merged["narrative"] = narrative
        if merged.get("time_delta_seconds") is None:
            merged["time_delta_seconds"] = prev_props.get("time_delta_seconds") or next_props.get(
                "time_delta_seconds"
            )
        by_pair[key] = GraphEdge(
            id=existing.id,
            **{"from": existing.from_},
            to=existing.to,
            label="CAUSED",
            properties=merged,
        )
    return rest + list(by_pair.values())


def _parse_timestamp(props: dict[str, Any]) -> datetime:
    raw = props.get("timestamp")
    if raw is None:
        return datetime.min
    if isinstance(raw, datetime):
        return raw
    if isinstance(raw, str):
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return datetime.min
    return datetime.min


def _alert_label(props: dict[str, Any]) -> str:
    name = props.get("name") or props.get("alert_row_id") or "Alert"
    risk = props.get("risk_score")
    if risk is not None:
        return f"Alert: {name} ({risk})"
    return f"Alert: {name}"


def _time_delta_seconds(prev: dict[str, Any], curr: dict[str, Any]) -> Optional[int]:
    t0 = _parse_timestamp(prev)
    t1 = _parse_timestamp(curr)
    if t0 == datetime.min or t1 == datetime.min:
        return None
    return max(0, int((t1 - t0).total_seconds()))


def _bridge_text(delta: Optional[int]) -> str:
    if delta is None:
        return "Correlated Sequence"
    if delta < 60:
        return f"Sequential Step (+{delta}s)"
    minutes = delta // 60
    if minutes < 60:
        return f"Sequential Step (+{minutes}m)"
    hours = minutes // 60
    if hours < 48:
        remainder_m = minutes % 60
        if remainder_m:
            return f"Sequential Step (+{hours}h {remainder_m}m)"
        return f"Sequential Step (+{hours}h)"
    days = hours // 24
    remainder_h = hours % 24
    if remainder_h:
        return f"Sequential Step (+{days}d {remainder_h}h)"
    return f"Sequential Step (+{days}d)"


def _build_caused_chain(
    alert_rows: list[dict[str, Any]],
) -> tuple[list[GraphNode], list[GraphEdge]]:
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []
    for row in alert_rows:
        labels = row.get("nlabels") or []
        if "Alert" not in labels:
            continue
        props = sanitize_neo4j_value(row.get("nprops") or {})
        group = list(labels) if labels else ["Alert"]
        nid = str(row["nid"])
        nodes.append(
            GraphNode(
                id=nid,
                label=str(props.get("name") or props.get("alert_row_id") or "Alert"),
                group=group,
                properties=props,
            )
        )
    for i in range(len(nodes) - 1):
        prev_props = nodes[i].properties
        curr_props = nodes[i + 1].properties
        delta = _time_delta_seconds(prev_props, curr_props)
        edges.append(
            GraphEdge(
                id=f"seq_{nodes[i].id}_{nodes[i + 1].id}",
                **{"from": nodes[i].id},
                to=nodes[i + 1].id,
                label="CAUSED",
                properties={
                    "time_delta_seconds": delta,
                    "confidence": "chronological_sequence",
                    "narrative": _bridge_text(delta),
                },
            )
        )
    return nodes, edges


def build_alert_centric_tree(
    nodes: list[GraphNode],
    _edges: list[GraphEdge],
) -> list[GraphTreeNode]:
    """Flat chronological attack_trees from alert-only CAUSED chain."""
    alert_nodes = [n for n in nodes if "Alert" in n.group]
    alert_nodes.sort(key=lambda n: _parse_timestamp(n.properties))

    trees: list[GraphTreeNode] = []
    for i, node in enumerate(alert_nodes, start=1):
        props = node.properties
        edge_context: Optional[str] = None
        if i > 1:
            delta = _time_delta_seconds(alert_nodes[i - 2].properties, props)
            edge_context = _bridge_text(delta)

        trees.append(
            GraphTreeNode(
                step=str(i),
                node_id=node.id,
                name=_alert_label(props),
                type="Alert",
                timestamp=str(props.get("timestamp") or ""),
                risk_score=int(props["risk_score"])
                if props.get("risk_score") is not None
                else None,
                edge_context=edge_context,
                children=[],
                expandable=False,
            )
        )
    return trees


async def build_alert_centric_topology(
    finding_id: str,
) -> GraphExplorationResponse | None:
    finding = await get_finding(finding_id)
    if finding is None:
        return None

    details = finding.details or {}
    incident_id = details.get("incident_id")
    if not incident_id:
        return GraphExplorationResponse(
            nodes=[],
            edges=[],
            highlight_info=HighlightInfo(),
            message=(
                "No incident_id on finding; alert-centric view requires an incident-bound finding."
            ),
        )

    alert_ids: list[str] = []
    for alert in details.get("contributing_alerts") or []:
        aid = alert.get("alert_row_id")
        if aid:
            alert_ids.append(str(aid))

    rows = await run_read_query(
        _INCIDENT_ALERTS_QUERY,
        {"incident_id": str(incident_id), "alert_ids": alert_ids},
    )
    used_fallback = False
    if not rows and alert_ids:
        rows = await run_read_query(_ALERTS_BY_ID_QUERY, {"alert_ids": alert_ids})
        used_fallback = bool(rows)

    if not rows:
        return GraphExplorationResponse(
            nodes=[],
            edges=[],
            highlight_info=HighlightInfo(),
            message=(
                f"No alerts linked to incident {incident_id} in Neo4j. "
                "Seed PART_OF_INCIDENT edges for demo data."
            ),
        )

    caused_nodes, caused_edges = _build_caused_chain(rows)
    if used_fallback:
        subgraph_rows = await run_read_query(
            _ALERTS_SUBGRAPH_QUERY,
            {"alert_ids": alert_ids},
        )
    else:
        subgraph_rows = await run_read_query(
            _INCIDENT_SUBGRAPH_QUERY,
            {"incident_id": str(incident_id), "alert_ids": alert_ids},
        )
    nodes, edges = _merge_subgraph_rows(caused_nodes, caused_edges, subgraph_rows)
    edges = _dedupe_parallel_caused_edges(edges)
    notifications: list[str] = []
    if used_fallback:
        notifications.append(
            "Loaded alerts by contributing_alerts (incident not yet linked in Neo4j)."
        )
    if alert_ids and len([n for n in nodes if "Alert" in n.group]) < len(alert_ids):
        notifications.append(
            "Some contributing_alerts were not found on the incident timeline in Neo4j."
        )

    return GraphExplorationResponse(
        nodes=nodes,
        edges=edges,
        highlight_info=HighlightInfo(),
        message="Success.",
        notifications=notifications or None,
    )


async def build_alert_centric_attack_tree(
    finding_id: str,
) -> AttackTreeResponse | None:
    topo = await build_alert_centric_topology(finding_id)
    if topo is None:
        return None
    if not topo.nodes:
        return AttackTreeResponse(
            attack_trees=[],
            message=topo.message or "No attack trees for this finding.",
            notifications=topo.notifications,
        )
    trees = build_alert_centric_tree(
        [n for n in topo.nodes if "Alert" in n.group],
        [e for e in topo.edges if e.label == "CAUSED"],
    )
    return AttackTreeResponse(
        attack_trees=trees,
        message="Success.",
        notifications=topo.notifications,
    )
