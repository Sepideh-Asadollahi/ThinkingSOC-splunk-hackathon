"""Observability analysis models for IT monitoring pipeline."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from models.enrichment import EnrichmentResult
from models.triage import TriageOutcome


class EntityResolution(BaseModel):
    resolved_host: Optional[str] = None
    resolved_service: Optional[str] = None
    resolved_asset_id: Optional[str] = None
    confidence: Literal["high", "medium", "low"]
    notes: str


class ImpactContext(BaseModel):
    impact_level: Literal["low", "medium", "high", "critical"]
    affected_entities: List[str] = Field(default_factory=list)
    customer_impact: str
    business_criticality: str
    time_window: str = "around alert window"


class RootCauseHypothesis(BaseModel):
    hypothesis: str
    confidence: Literal["high", "medium", "low"]
    evidence_refs: List[str] = Field(default_factory=list)
    what_would_confirm: Optional[str] = None


class DiagnoserSection(BaseModel):
    root_cause_hypotheses: List[RootCauseHypothesis] = Field(default_factory=list)
    followup_searches: List[str] = Field(default_factory=list)


class ResponderSection(BaseModel):
    recommended_actions: List[str] = Field(default_factory=list)
    safety_notes: List[str] = Field(default_factory=list)


class OpsJudgeVerdict(BaseModel):
    verdict: str
    priority: str
    recommended_next_step: str
    confidence: Literal["high", "medium", "low"]
    rationale: str
    escalation_target: Optional[str] = None


class ObservabilityAnalysisResult(BaseModel):
    track: Literal["observability"] = "observability"
    summary: str
    entity_resolution: EntityResolution
    impact_context: ImpactContext
    diagnoser: DiagnoserSection
    responder: ResponderSection
    ops_judge: OpsJudgeVerdict
    evidence_refs: List[str] = Field(default_factory=list)
    triage: Optional[TriageOutcome] = Field(
        default=None,
        description="Post-analysis priority and review verdict for analyst queue.",
    )


class ObservabilityRunRequest(BaseModel):
    normalized: Dict[str, Any] = Field(default_factory=dict)
    search_name: Optional[str] = None
    sid: Optional[str] = None
    row_index: Optional[int] = Field(default=None, ge=0)
    splunk_results: List[Dict[str, Any]] = Field(default_factory=list)

    enrichment: Optional[EnrichmentResult] = None
    users: Optional[List[Dict[str, Any]]] = None
    assets: Optional[List[Dict[str, Any]]] = None
    relationships: Optional[List[Dict[str, Any]]] = None


class ObservabilityBatchBySidRequest(BaseModel):
    sid: str
    search_name: Optional[str] = None
    normalized: Dict[str, Any] = Field(default_factory=dict)
    users: Optional[List[Dict[str, Any]]] = None
    assets: Optional[List[Dict[str, Any]]] = None
    relationships: Optional[List[Dict[str, Any]]] = None
    max_rows: int = Field(100, ge=1, le=500)
    stop_on_first_error: bool = False


class RowObservabilityOutcome(BaseModel):
    row_index: int
    ok: bool
    error: Optional[str] = None
    result: Optional[ObservabilityAnalysisResult] = None


class ObservabilityBatchBySidResponse(BaseModel):
    sid: str
    search_name: Optional[str] = None
    splunk_results_row_count: int
    analyzed_row_count: int
    rows: List[RowObservabilityOutcome] = Field(default_factory=list)
