from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class GraphFindingSummary(BaseModel):
    id: str
    display_id: str
    finding_type: str
    title: str
    summary: str
    risk_score: int
    created_at: datetime
    ticket_status: str
    owner: str
    updated_at: Optional[datetime] = None
    agent_validation_status: Optional[str] = None


class PaginatedGraphFindingsResponse(BaseModel):
    items: list[GraphFindingSummary]
    total: int
    limit: int
    offset: int


class GraphFindingDetails(GraphFindingSummary):
    details: dict[str, Any] = Field(default_factory=dict)
    status: Optional[str] = None


class PatchFindingTicketRequest(BaseModel):
    ticket_status: Optional[str] = None
    assigned_to_user_id: Optional[str] = None
    new_note: Optional[str] = None
