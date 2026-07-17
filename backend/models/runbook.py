"""Verified incident-to-runbook contracts used by the Forge MVP."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from models.analysis import InvestigationQuestionItem


class RunbookStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step_id: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=160)
    intent: str = Field(min_length=1, max_length=2000)
    expected_evidence: str = Field(min_length=1, max_length=1000)
    stop_condition: str = Field(min_length=1, max_length=1000)


class VerifiedRunbookDraft(BaseModel):
    runbook_id: str
    source_record_id: int
    title: str
    summary: str
    applicable_search_name: str
    source_verdict: str
    steps: List[RunbookStep] = Field(min_length=1, max_length=3)
    decision_rule: str
    limitations: List[str] = Field(default_factory=list)
    source_results: List[InvestigationQuestionItem] = Field(default_factory=list)
    status: Literal["DRAFT", "PARSER_VALID", "SOURCE_VERIFIED", "FAILED"]
    configured_model: Optional[str] = None
    model: str
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    generation_duration_ms: int = Field(default=0, ge=0)
    verification_duration_ms: int = Field(default=0, ge=0)
    compile_duration_ms: int = Field(ge=0)
    parser_valid_step_count: int = Field(default=0, ge=0)
    successful_step_count: int = Field(default=0, ge=0)
    total_evidence_rows: int = Field(default=0, ge=0)
    revision: int = Field(default=1, ge=1)
    parent_runbook_id: Optional[str] = None
    origin: Literal["compiled", "edited", "imported"] = "compiled"
    revision_note: Optional[str] = None
    edited_by: Optional[str] = None
    imported_from_runbook_id: Optional[str] = None
    created_at: str


class RunbookEditableContent(BaseModel):
    """Portable, intent-only runbook content that an analyst may edit."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    summary: str = Field(min_length=1, max_length=2000)
    applicable_search_name: str = Field(min_length=1, max_length=500)
    steps: List[RunbookStep] = Field(min_length=1, max_length=3)
    decision_rule: str = Field(min_length=1, max_length=2000)
    limitations: List[str] = Field(default_factory=list, max_length=10)


class RunbookRevisionBody(RunbookEditableContent):
    """Create a new immutable revision; an existing artifact is never overwritten."""

    source_record_id: Optional[int] = Field(default=None, gt=0)
    verify_on_source: bool = False
    revision_note: Optional[str] = Field(default=None, max_length=2000)
    editor: str = Field(default="analyst", min_length=1, max_length=128)


class PortableRunbook(RunbookEditableContent):
    """Evidence-free JSON representation safe to move between deployments."""

    original_runbook_id: Optional[str] = None
    original_source_record_id: Optional[int] = None
    source_verdict: str = Field(default="needs_investigation", max_length=200)
    revision: int = Field(default=1, ge=1)
    created_at: Optional[str] = None


class RunbookExportBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["thinking-soc.runbook-library/v1"] = (
        "thinking-soc.runbook-library/v1"
    )
    exported_at: str
    runbooks: List[PortableRunbook] = Field(min_length=1, max_length=100)


class RunbookImportBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document: RunbookExportBundle
    source_record_id: Optional[int] = Field(default=None, gt=0)
    verify_on_source: bool = False
    imported_by: str = Field(default="analyst", min_length=1, max_length=128)
    note: Optional[str] = Field(default=None, max_length=2000)


class RunbookApprovalBody(BaseModel):
    runbook_id: str = Field(min_length=1, max_length=128)
    decision: Literal["approve", "reject"]
    note: Optional[str] = Field(default=None, max_length=2000)
    analyst: str = Field(default="analyst", min_length=1, max_length=128)


class RunbookApproval(BaseModel):
    runbook_id: str
    source_record_id: int
    decision: Literal["approve", "reject"]
    analyst: str = "analyst"
    note: Optional[str] = None
    created_at: str


class RunbookRunBody(BaseModel):
    source_record_id: int = Field(gt=0)
    runbook_id: str = Field(min_length=1, max_length=128)
    estimated_manual_minutes: int = Field(default=25, ge=5, le=120)


class RunbookRun(BaseModel):
    runbook_id: str
    source_record_id: int
    target_record_id: int
    status: Literal["REUSED", "NO_EVIDENCE", "FAILED"]
    results: List[InvestigationQuestionItem] = Field(default_factory=list)
    duration_ms: int = Field(ge=0)
    estimated_manual_minutes: int = Field(ge=5, le=120)
    estimated_minutes_saved: float = Field(ge=0)
    savings_percent: float = Field(default=0, ge=0, le=100)
    successful_step_count: int = Field(default=0, ge=0)
    total_evidence_rows: int = Field(default=0, ge=0)
    created_at: str


class RunbookShadowBody(BaseModel):
    """Read-only pre-approval replay against a distinct historical alert."""

    source_record_id: int = Field(gt=0)
    runbook_id: str = Field(min_length=1, max_length=128)
    estimated_manual_minutes: int = Field(default=25, ge=5, le=120)


class RunbookShadowRun(BaseModel):
    shadow_run_id: str
    runbook_id: str
    source_record_id: int
    target_record_id: int
    source_sid: Optional[str] = None
    target_sid: Optional[str] = None
    search_name: str
    status: Literal["EVIDENCE_FOUND", "NO_EVIDENCE", "FAILED"]
    results: List[InvestigationQuestionItem] = Field(default_factory=list)
    duration_ms: int = Field(ge=0)
    estimated_manual_minutes: int = Field(ge=5, le=120)
    projected_minutes_saved: float = Field(ge=0)
    projected_labor_savings_usd: float = Field(ge=0)
    parser_valid_step_count: int = Field(default=0, ge=0)
    successful_step_count: int = Field(default=0, ge=0)
    total_evidence_rows: int = Field(default=0, ge=0)
    execution_error_count: int = Field(default=0, ge=0)
    failure_reason: Optional[str] = Field(default=None, max_length=500)
    created_at: str


class RunbookShadowRunSummary(BaseModel):
    shadow_run_id: str
    runbook_id: str
    source_record_id: int
    target_record_id: int
    target_sid: Optional[str] = None
    search_name: str
    status: Literal["EVIDENCE_FOUND", "NO_EVIDENCE", "FAILED"]
    duration_ms: int = Field(ge=0)
    projected_minutes_saved: float = Field(ge=0)
    projected_labor_savings_usd: float = Field(ge=0)
    parser_valid_step_count: int = Field(default=0, ge=0)
    successful_step_count: int = Field(default=0, ge=0)
    total_evidence_rows: int = Field(default=0, ge=0)
    execution_error_count: int = Field(default=0, ge=0)
    failure_reason: Optional[str] = Field(default=None, max_length=500)
    created_at: str


class SafeResponsePreviewBody(BaseModel):
    """Request a non-executable response recommendation for one runbook revision."""

    runbook_id: str = Field(min_length=1, max_length=128)


class SafeResponseAction(BaseModel):
    """High-level manual response option; executable syntax is intentionally absent."""

    model_config = ConfigDict(extra="forbid")

    action_id: str = Field(min_length=1, max_length=64)
    action_type: Literal[
        "ISOLATE_ENDPOINT",
        "DISABLE_ACCOUNT",
        "REVOKE_SESSIONS",
        "BLOCK_INDICATOR",
        "QUARANTINE_FILE",
        "COLLECT_FORENSICS",
        "ESCALATE_INCIDENT",
        "MONITOR_ONLY",
    ]
    title: str = Field(min_length=1, max_length=200)
    target_type: Literal["endpoint", "identity", "ip", "domain", "file", "incident"]
    target: str = Field(min_length=1, max_length=500)
    risk_level: Literal["low", "medium", "high", "critical"]
    rationale: str = Field(min_length=1, max_length=2000)
    prerequisites: List[str] = Field(default_factory=list, max_length=8)
    expected_effect: str = Field(min_length=1, max_length=1000)
    rollback_plan: str = Field(min_length=1, max_length=1000)
    verification_steps: List[str] = Field(min_length=1, max_length=8)
    requires_human_approval: Literal[True] = True
    execution_mode: Literal["PREVIEW_ONLY"] = "PREVIEW_ONLY"


class SafeResponsePreview(BaseModel):
    preview_id: str
    runbook_id: str
    source_record_id: int
    source_verdict: str
    status: Literal["READY_FOR_REVIEW"] = "READY_FOR_REVIEW"
    evidence_basis: Literal["SOURCE_EVIDENCE", "ANALYSIS_ONLY"]
    actions: List[SafeResponseAction] = Field(min_length=1, max_length=5)
    decision_summary: str = Field(min_length=1, max_length=2000)
    limitations: List[str] = Field(default_factory=list, max_length=10)
    configured_model: Optional[str] = None
    model: str
    prompt_tokens: Optional[int] = Field(default=None, ge=0)
    completion_tokens: Optional[int] = Field(default=None, ge=0)
    generation_duration_ms: int = Field(default=0, ge=0)
    execution_supported: Literal[False] = False
    created_at: str


class SafeResponseDecisionBody(BaseModel):
    preview_id: str = Field(min_length=1, max_length=128)
    decision: Literal["approve_for_manual_action", "reject"]
    note: Optional[str] = Field(default=None, max_length=2000)
    analyst: str = Field(default="analyst", min_length=1, max_length=128)


class SafeResponseDecision(BaseModel):
    preview_id: str
    runbook_id: str
    source_record_id: int
    decision: Literal["approve_for_manual_action", "reject"]
    analyst: str
    note: Optional[str] = None
    automatic_execution_performed: Literal[False] = False
    created_at: str


class RunbookAutopilotBody(BaseModel):
    """Run a bounded, observable agent workflow for one investigation."""

    objective: str = Field(
        default="Assess the investigation and advance its reusable runbook safely.",
        min_length=1,
        max_length=1000,
    )
    mode: Literal["ASSESS", "ADVANCE"] = "ADVANCE"
    generate_response_preview: bool = True


class RunbookAutopilotEvent(BaseModel):
    """One immutable handoff, tool call, result, or policy decision."""

    event_id: str
    sequence: int = Field(ge=1)
    agent: Literal[
        "SUPERVISOR",
        "EVIDENCE_SCOUT",
        "RUNBOOK_ENGINEER",
        "POLICY_GUARD",
        "RESPONSE_ADVISOR",
    ]
    kind: Literal[
        "AGENT_STARTED",
        "HANDOFF",
        "TOOL_CALL",
        "TOOL_RESULT",
        "POLICY_DECISION",
        "AGENT_COMPLETED",
    ]
    status: Literal["RUNNING", "SUCCEEDED", "BLOCKED", "FAILED"]
    summary: str = Field(min_length=1, max_length=1000)
    tool_name: Optional[str] = Field(default=None, max_length=128)
    duration_ms: int = Field(default=0, ge=0)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: str


class RunbookAutopilotSession(BaseModel):
    """Durable audit record for the bounded Runbook Autopilot workflow."""

    session_id: str
    source_record_id: int
    objective: str
    mode: Literal["ASSESS", "ADVANCE"]
    status: Literal[
        "COMPLETED",
        "AWAITING_HUMAN_APPROVAL",
        "BLOCKED",
        "FAILED",
    ]
    agents: List[str] = Field(default_factory=list)
    tools_used: List[str] = Field(default_factory=list)
    trace: List[RunbookAutopilotEvent] = Field(default_factory=list, max_length=64)
    runbook_id: Optional[str] = None
    runbook_status: Optional[str] = None
    response_preview_id: Optional[str] = None
    next_recommended_action: str = Field(min_length=1, max_length=1000)
    human_approval_required: Literal[True] = True
    automatic_execution_performed: Literal[False] = False
    started_at: str
    completed_at: str
    duration_ms: int = Field(ge=0)


class RunbookEvaluationResponse(BaseModel):
    generated_at: str
    revision_count: int = Field(ge=0)
    alert_count: int = Field(ge=0)
    latest_runbook_count: int = Field(ge=0)
    approved_runbook_count: int = Field(ge=0)
    production_run_count: int = Field(ge=0)
    shadow_run_count: int = Field(ge=0)
    source_verified_revision_count: int = Field(ge=0)
    parser_valid_revision_count: int = Field(ge=0)
    failed_revision_count: int = Field(ge=0)
    total_step_count: int = Field(ge=0)
    parser_valid_step_count: int = Field(ge=0)
    parser_valid_rate: float = Field(ge=0, le=100)
    shadow_evidence_run_count: int = Field(ge=0)
    evidence_coverage_rate: float = Field(ge=0, le=100)
    total_shadow_evidence_rows: int = Field(ge=0)
    total_execution_errors: int = Field(ge=0)
    average_compile_duration_ms: float = Field(ge=0)
    average_shadow_duration_ms: float = Field(ge=0)
    projected_minutes_saved: float = Field(ge=0)
    projected_labor_savings_usd: float = Field(ge=0)
    realized_minutes_saved: float = Field(ge=0)
    total_prompt_tokens: int = Field(ge=0)
    total_completion_tokens: int = Field(ge=0)
    estimated_compile_llm_cost_usd: float = Field(ge=0)
    analyst_hourly_cost_usd: float = Field(ge=0)
    shadow_status_breakdown: Dict[str, int] = Field(default_factory=dict)
    recent_shadow_runs: List[RunbookShadowRunSummary] = Field(default_factory=list)


class VerifiedRunbookState(BaseModel):
    record_id: int
    draft: Optional[VerifiedRunbookDraft] = None
    latest_approval: Optional[RunbookApproval] = None
    latest_run: Optional[RunbookRun] = None
    latest_response_preview: Optional[SafeResponsePreview] = None
    latest_response_decision: Optional[SafeResponseDecision] = None


class RunbookLibraryItem(BaseModel):
    draft: VerifiedRunbookDraft
    latest_approval: Optional[RunbookApproval] = None
    latest_run: Optional[RunbookRun] = None
    is_latest_for_source: bool = False


class RunbookLibraryGroup(BaseModel):
    alert_name: str
    count: int = Field(ge=0)
    runbooks: List[RunbookLibraryItem] = Field(default_factory=list)


class RunbookLibraryResponse(BaseModel):
    count: int = Field(ge=0)
    alert_count: int = Field(ge=0)
    groups: List[RunbookLibraryGroup] = Field(default_factory=list)


class RunbookImportResponse(BaseModel):
    imported_count: int = Field(ge=0)
    runbooks: List[VerifiedRunbookDraft] = Field(default_factory=list)


class RunbookRuntimeStatus(BaseModel):
    enabled: bool
    autopilot_enabled: bool = True
    ready: bool
    configured_model: str
    max_steps: int = Field(ge=1, le=3)
    default_manual_minutes: int = Field(ge=5, le=120)
    artifact_scan_limit: int = Field(ge=50, le=1000)
    postgres_configured: bool
    llm_configured: bool
    splunk_configured: bool
    mcp_configured: bool
    rest_api_configured: bool
    execution_transport_policy: Literal["mcp_then_rest"] = "mcp_then_rest"
    execution_enabled: bool
    acknowledgment_required: Literal[True] = True
    exact_search_name_required: Literal[True] = True
    source_evidence_required: Literal[True] = True


class RunbookCompatibleTarget(BaseModel):
    """Minimal, non-sensitive target metadata used by the guided-reuse picker."""

    record_id: int
    created_at: Optional[str] = None
    sid: Optional[str] = None
    search_name: str
    row_index: Optional[int] = None
    summary: Optional[str] = None
    review_verdict: Optional[str] = None


class RunbookCompatibleTargets(BaseModel):
    source_record_id: int
    search_name: str
    count: int = Field(ge=0)
    results: List[RunbookCompatibleTarget] = Field(default_factory=list)
