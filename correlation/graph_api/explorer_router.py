from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from graph_api.deps import require_bearer
from graph_crud.alert_centric import build_alert_centric_attack_tree
from graph_crud.topology import build_topology_for_finding
from graph_schemas.exploration import AttackTreeResponse, GraphExplorationResponse

router = APIRouter(tags=["explorer"])


@router.get("/topology/{identifier}", response_model=GraphExplorationResponse)
async def get_topology(
    identifier: str,
    _: None = Depends(require_bearer),
) -> GraphExplorationResponse:
    topo = await build_topology_for_finding(identifier)
    if topo is None:
        raise HTTPException(status_code=404, detail="Finding not found")
    return topo


@router.get("/attack-tree/{identifier}", response_model=AttackTreeResponse)
async def get_attack_tree(
    identifier: str,
    _: None = Depends(require_bearer),
) -> AttackTreeResponse:
    result = await build_alert_centric_attack_tree(identifier)
    if result is None:
        raise HTTPException(status_code=404, detail="Finding not found")
    return result
