from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from graph_api.deps import require_bearer
from graph_crud.findings import get_finding, list_findings, patch_finding_ticket
from graph_crud.schema import prune_correlation_findings_to_canonical
from graph_crud.topology import build_topology_for_finding
from graph_schemas.finding import (
    GraphFindingDetails,
    PaginatedGraphFindingsResponse,
    PatchFindingTicketRequest,
)
from graph_schemas.exploration import GraphExplorationResponse

router = APIRouter(prefix="/findings", tags=["findings"])


@router.get("", response_model=PaginatedGraphFindingsResponse)
async def get_findings(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    finding_type: Optional[str] = Query("smart_attack_discovery"),
    exclude_finding_type: Optional[str] = Query(None),
    _: None = Depends(require_bearer),
) -> PaginatedGraphFindingsResponse:
    await prune_correlation_findings_to_canonical()
    return await list_findings(
        limit=limit,
        offset=offset,
        finding_type=finding_type,
        exclude_finding_type=exclude_finding_type,
    )


@router.get("/{finding_id}/graph-data", response_model=GraphExplorationResponse)
async def get_finding_graph_data(
    finding_id: str,
    _: None = Depends(require_bearer),
) -> GraphExplorationResponse:
    topo = await build_topology_for_finding(finding_id)
    if topo is None:
        raise HTTPException(status_code=404, detail="Finding not found")
    if not topo.nodes:
        raise HTTPException(status_code=404, detail="No graph data for finding")
    return topo


@router.patch("/{finding_id}/ticket", response_model=GraphFindingDetails)
async def patch_ticket(
    finding_id: str,
    body: PatchFindingTicketRequest,
    _: None = Depends(require_bearer),
) -> GraphFindingDetails:
    row = await patch_finding_ticket(finding_id, body)
    if row is None:
        raise HTTPException(status_code=404, detail="Finding not found")
    return row


@router.get("/{finding_id}", response_model=GraphFindingDetails)
async def get_finding_by_id(
    finding_id: str,
    _: None = Depends(require_bearer),
) -> GraphFindingDetails:
    row = await get_finding(finding_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Finding not found")
    return row
