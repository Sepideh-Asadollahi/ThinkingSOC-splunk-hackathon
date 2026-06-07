from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class CorrelatedAlert(BaseModel):
    alert_row_id: str
    name: str
    status: str
    risk_score: int
    timestamp: str
    entities_in_common: list[str] = Field(default_factory=list)


class CorrelateRequest(BaseModel):
    entity_identifiers: list[str]
    current_alert_row_id: str
    depth: int = Field(default=2, ge=1, le=4)
    max_questions: int = 0


class CorrelateResponse(BaseModel):
    correlated_alerts: list[CorrelatedAlert]
    total_found: int
    suggested_queries: list[str] = Field(default_factory=list)


class GraphNode(BaseModel):
    id: str
    label: str
    group: list[str] = Field(default_factory=list)
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    id: str
    from_: str = Field(alias="from")
    to: str
    label: str
    properties: dict[str, Any] = Field(default_factory=dict)

    model_config = {"populate_by_name": True}


class HighlightInfo(BaseModel):
    node_ids: list[str] = Field(default_factory=list)
    edge_ids: list[str] = Field(default_factory=list)


class GraphExplorationResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    highlight_info: HighlightInfo = Field(default_factory=HighlightInfo)
    message: str = "Success."
    notifications: Optional[list[str]] = None


class GraphTreeNode(BaseModel):
    step: str
    node_id: str
    name: str
    type: str
    timestamp: Optional[str] = None
    risk_score: Optional[int] = None
    edge_context: Optional[str] = None
    expandable: bool = False
    children: list["GraphTreeNode"] = Field(default_factory=list)


class AttackTreeResponse(BaseModel):
    attack_trees: list[GraphTreeNode]
    message: str = "Success."
    notifications: Optional[list[str]] = None
