from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from graph_api.deps import require_bearer
from graph_core.operation_store import operation_store
from graph_pipelines.demo_smart_analysis import run_demo_smart_analysis
from graph_schemas.analysis import (
    DiscoverAttackPathsRequest,
    DiscoverAttackPathsResponse,
    OperationStatusResponse,
)

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.post(
    "/discover-attack-paths",
    response_model=DiscoverAttackPathsResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def discover_attack_paths(
    body: DiscoverAttackPathsRequest,
    background_tasks: BackgroundTasks,
    _: None = Depends(require_bearer),
) -> DiscoverAttackPathsResponse:
    operation_id = await operation_store.create()
    background_tasks.add_task(
        run_demo_smart_analysis,
        operation_id,
        limit_to_latest_alerts=body.limit_to_latest_alerts,
        force_reanalysis=body.force_reanalysis,
    )
    return DiscoverAttackPathsResponse(operation_id=operation_id)


@router.get("/operations/{operation_id}/status", response_model=OperationStatusResponse)
async def get_operation_status(
    operation_id: str,
    _: None = Depends(require_bearer),
) -> OperationStatusResponse:
    op = await operation_store.get(operation_id)
    if op is None:
        raise HTTPException(status_code=404, detail="Operation not found")
    return op
