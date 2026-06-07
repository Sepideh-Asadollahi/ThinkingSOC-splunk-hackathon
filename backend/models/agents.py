"""Agent-style triage endpoint models."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from models.agentic_ops import AlertClassificationResult
from models.analysis import SocAnalysisResult
from models.assistant import SplAssistantSuggestResponse
from models.mcp import McpAlertContext
from models.observability import ObservabilityAnalysisResult
from models.triage import TriageOutcome


class AgentTriageRequest(BaseModel):
    normalized: Dict[str, Any] = Field(default_factory=dict)
    search_name: Optional[str] = None
    sid: Optional[str] = None
    row_index: Optional[int] = Field(default=None, ge=0)
    job_row_count: Optional[int] = Field(
        default=None,
        ge=1,
        description="Total Splunk job rows when splunk_results is a single-row slice.",
    )
    splunk_results: List[Dict[str, Any]] = Field(default_factory=list)
    operator_goal: Optional[str] = None

    users: Optional[List[Dict[str, Any]]] = None
    assets: Optional[List[Dict[str, Any]]] = None
    relationships: Optional[List[Dict[str, Any]]] = None


class AgentTriageResponse(BaseModel):
    track: str
    classification: AlertClassificationResult
    agent_summary: str
    next_actions: List[str] = Field(default_factory=list)
    security_result: Optional[SocAnalysisResult] = None
    observability_result: Optional[ObservabilityAnalysisResult] = None
    suggested_spl: Optional[SplAssistantSuggestResponse] = None
    mcp_used: bool = False
    mcp_context: Optional[McpAlertContext] = None
    security_triage: Optional[TriageOutcome] = None
    observability_triage: Optional[TriageOutcome] = None

