from __future__ import annotations

from fastapi import APIRouter, Depends

from graph_api.deps import require_demo_api_key
from graph_crud.correlation import find_correlated_alerts
from graph_schemas.exploration import CorrelateRequest, CorrelateResponse

router = APIRouter(prefix="/internal", tags=["internal"])


@router.post("/correlate", response_model=CorrelateResponse)
async def correlate(
    body: CorrelateRequest,
    _: None = Depends(require_demo_api_key),
) -> CorrelateResponse:
    return await find_correlated_alerts(body)
