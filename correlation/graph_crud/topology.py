from __future__ import annotations

from graph_crud.alert_centric import build_alert_centric_topology
from graph_schemas.exploration import GraphExplorationResponse


async def build_topology_for_finding(
    finding_id: str,
) -> GraphExplorationResponse | None:
    return await build_alert_centric_topology(finding_id)
