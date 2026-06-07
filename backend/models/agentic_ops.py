"""Shared models for alert routing between Security and Observability."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from models.analysis import SocAnalysisResult
from models.enrichment import EnrichmentResult
from models.mcp import McpAlertContext
from models.observability import ObservabilityAnalysisResult


class AlertClassificationResult(BaseModel):
    track: Literal["security", "observability", "both", "unknown"]
    recommended_pipeline: Literal["security", "observability", "dual", "manual_review"]
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str
    signals: List[str] = Field(default_factory=list)
    secondary_track: Optional[Literal["security", "observability"]] = None
    needs_human_routing: bool = False
    classification_source: Literal["rules", "llm", "hybrid"] = "rules"


class AnalysisRouteRequest(BaseModel):
    normalized: Dict[str, Any] = Field(default_factory=dict)
    search_name: Optional[str] = None
    sid: Optional[str] = None
    row_index: Optional[int] = Field(
        default=None,
        ge=0,
        description="Which Splunk result row to analyze (default 0). Use run-by-sid for all rows.",
    )
    splunk_results: List[Dict[str, Any]] = Field(default_factory=list)

    enrichment: Optional[EnrichmentResult] = None
    users: Optional[List[Dict[str, Any]]] = None
    assets: Optional[List[Dict[str, Any]]] = None
    relationships: Optional[List[Dict[str, Any]]] = None


class AlertClassificationRequest(BaseModel):
    normalized: Dict[str, Any] = Field(default_factory=dict)
    search_name: Optional[str] = None
    sid: Optional[str] = None
    splunk_results: List[Dict[str, Any]] = Field(default_factory=list)


class AnalysisRouteResponse(BaseModel):
    track: Literal["security", "observability", "both", "unknown"]
    classification: AlertClassificationResult
    security_result: Optional[SocAnalysisResult] = None
    observability_result: Optional[ObservabilityAnalysisResult] = None
    mcp_used: bool = False
    mcp_context: Optional[McpAlertContext] = None
    row_index: int = 0
    raw_alert: Dict[str, Any] = Field(default_factory=dict)
    analysis_input: Dict[str, Any] = Field(default_factory=dict)
    analysis_output: Optional[Dict[str, Any]] = None
