from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class DiscoverAttackPathsRequest(BaseModel):
    analysis_types: list[str] = Field(default_factory=lambda: ["smart"])
    limit_to_latest_alerts: int = Field(default=50, ge=1, le=500)
    force_reanalysis: bool = True


class DiscoverAttackPathsResponse(BaseModel):
    message: str = "Task Initiated"
    operation_id: str


class OperationLogEntry(BaseModel):
    timestamp: datetime
    level: str = "info"
    message: str


class OperationStatusResponse(BaseModel):
    operation_id: str
    operation_type: str = "manual_attack_discovery"
    status: Literal["running", "completed", "failed"]
    message: str
    detailed_logs: list[OperationLogEntry] = Field(default_factory=list)
    result_payload: Optional[dict[str, Any]] = None
    created_at: datetime
    last_updated: datetime


class SmartAnalysisSummary(BaseModel):
    clusters: int = 0
    merged_incidents: int = 0
    alerts_processed: int = 0
