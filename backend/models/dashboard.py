"""Dashboard overview API models."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class DashboardKpis(BaseModel):
    total_records: int = 0
    analyses_24h: int = 0
    needs_human_review: int = 0
    avg_triage_score: float = 0.0
    users: int = 0
    assets: int = 0


class ActivityTimelinePoint(BaseModel):
    date: str
    security: int = 0
    observability: int = 0
    correlation: int = 0
    other: int = 0


class CountByType(BaseModel):
    type: str
    count: int


class CountByVerdict(BaseModel):
    verdict: str
    count: int


class CountByPriority(BaseModel):
    priority: str
    count: int


class TrackSplit(BaseModel):
    security: int = 0
    observability: int = 0


class DashboardIntegrations(BaseModel):
    postgres: bool = False
    llm: bool = False
    mcp: bool = False
    neo4j: bool = False


class DashboardRunbookOps(BaseModel):
    """ThinkingSOC Lite, guarded reuse, Autopilot, and Chat operational rollup."""

    latest_runbooks: int = 0
    source_verified: int = 0
    human_approved: int = 0
    reusable_alert_names: int = 0
    executions: int = 0
    reused: int = 0
    no_evidence: int = 0
    failed: int = 0
    evidence_rows: int = 0
    estimated_minutes_saved: float = 0.0
    shadow_runs: int = 0
    response_previews: int = 0
    autopilot_sessions: int = 0
    autopilot_completed: int = 0
    chat_conversations: int = 0
    chat_messages: int = 0


class SystemResources(BaseModel):
    hostname: str = ""
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_used_bytes: int = 0
    memory_total_bytes: int = 0


class TopPriorityItem(BaseModel):
    id: Optional[int] = None
    stored_at: Optional[str] = None
    tsoc_record_type: Optional[str] = None
    sid: Optional[str] = None
    search_name: Optional[str] = None
    row_index: Optional[int] = None
    source_track: Optional[str] = None
    triage_score: int = 0
    investigation_priority: Optional[str] = None
    review_verdict: Optional[str] = None
    needs_human_review: bool = False


class DashboardOverview(BaseModel):
    generated_at: str
    postgres_configured: bool
    system_resources: SystemResources = Field(default_factory=SystemResources)
    kpis: DashboardKpis
    activity_timeline: List[ActivityTimelinePoint] = Field(default_factory=list)
    record_type_counts: List[CountByType] = Field(default_factory=list)
    triage_by_verdict: List[CountByVerdict] = Field(default_factory=list)
    triage_by_priority: List[CountByPriority] = Field(default_factory=list)
    track_split: TrackSplit = Field(default_factory=TrackSplit)
    integrations: DashboardIntegrations = Field(default_factory=DashboardIntegrations)
    runbook_ops: DashboardRunbookOps = Field(default_factory=DashboardRunbookOps)
    health_score: int = 0
    top_priority: List[TopPriorityItem] = Field(default_factory=list)
