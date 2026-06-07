"""SOC Analysis output contract (LLD §5, 09-soc-analysis-service-hackathon.md)."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from models.admin_org import AdminOrgGapSuggestResponse
from models.enrichment import EnrichmentResult
from models.mcp import McpHunterEvidence, McpJudgeEvidence
from models.triage import TriageOutcome


class FrameworkMappingItem(BaseModel):
    framework: str = "MITRE ATT&CK"
    id: str
    name: str
    confidence: Literal["high", "medium", "low"]
    rationale: str


class JudgeVerdict(BaseModel):
    verdict: str
    priority: str
    recommended_next_step: str
    rationale: str
    confidence: Optional[Literal["high", "medium", "low"]] = None
    mcp_evidence: Optional[McpJudgeEvidence] = Field(
        default=None,
        description="Splunk MCP SAIA answers and verification queries used before Judge LLM verdict.",
    )


class HunterSection(BaseModel):
    """Hunter perspective + at least one Splunk search idea (Hackathon minimum)."""

    narrative: str
    splunk_search_suggestions: List[str] = Field(default_factory=list)
    mcp_evidence: Optional[McpHunterEvidence] = Field(
        default=None,
        description="Live Splunk MCP hunt queries/metadata used before Hunter LLM reasoning.",
    )


class RootCauseSplValidation(BaseModel):
    """Outcome of validating the generated SPL via Splunk ``/services/search/parser`` (no execution)."""

    method: Literal["splunk_parser", "skipped"]
    valid: Optional[bool] = None
    message: Optional[str] = None


class RootCauseSpl(BaseModel):
    """Splunk AI Assistant style SPL for root-cause hunting."""

    spl: str = Field(description="Full Splunk SPL string (single-line preferred); parameterized from normalized fields.")
    explanation: str = Field(default="", description="One-paragraph plain-English explanation of what the SPL does.")
    time_window: str = Field(
        default="",
        description="Splunk All Time bounds label, e.g. 'earliest=1 latest=now' (REST uses earliest_time=0).",
    )
    pivots: List[str] = Field(default_factory=list, description="normalized field names the SPL pivots on (e.g. host, src, user).")
    notes: List[str] = Field(default_factory=list, description="Optional caveats (missing fields, assumed indexes, etc.).")
    validation: Optional[RootCauseSplValidation] = None
    spl_results: Optional[SplSearchResult] = Field(
        default=None,
        description="Tabular MCP/REST execute results when TSOC_EXECUTE_INVESTIGATION_SPL is enabled.",
    )


class SplSearchResult(BaseModel):
    """Tabular output from executing investigation SPL on Splunk (oneshot)."""

    row_count: int = 0
    rows: List[Dict[str, Any]] = Field(default_factory=list)
    truncated: bool = False
    error: Optional[str] = None


class SplSaiaAnalysis(BaseModel):
    """SAIA MCP explain/optimize review for a generated investigation SPL."""

    explanation: str = Field(
        default="",
        description="Natural-language walkthrough from saia_explain_spl (Splunk AI Assistant).",
    )
    optimized: bool = Field(
        default=False,
        description="True when saia_optimize_spl returned a different runnable SPL.",
    )
    spl_before_optimize: Optional[str] = Field(
        default=None,
        description="Original SPL before SAIA optimization (when optimized=True).",
    )
    steps: List[str] = Field(
        default_factory=list,
        description="SAIA pipeline steps completed, e.g. optimize, explain.",
    )
    unavailable_reason: Optional[str] = Field(
        default=None,
        description="Set when MCP/SAIA tools were not available for this SPL.",
    )


class InvestigationQuestionItem(BaseModel):
    """One investigable question paired with Splunk SPL the analyst can run."""

    question: str
    spl: str
    cim_datamodel: Optional[str] = Field(
        default=None,
        description="CIM datamodel chosen for this question (from datamodelsimple catalog + selection).",
    )
    explanation: str = ""
    time_window: str = ""
    pivots: List[str] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)
    validation: Optional[RootCauseSplValidation] = None
    spl_results: Optional[SplSearchResult] = Field(
        default=None,
        description="Optional oneshot execution results when Splunk REST is configured.",
    )
    spl_results_analysis: Optional[Dict[str, Any]] = Field(
        default=None,
        description="LLM analysis of the executed SPL result batch for this question.",
    )
    spl_saia_analysis: Optional[SplSaiaAnalysis] = Field(
        default=None,
        description="SAIA MCP explain/optimize analysis for the generated SPL.",
    )


class EvidenceChain(BaseModel):
    """Traceable chain from source evidence to final security verdict."""

    request: Dict[str, Any] = Field(default_factory=dict)
    data_sources: Dict[str, Any] = Field(default_factory=dict)
    reasoning_path: Dict[str, Any] = Field(default_factory=dict)
    decision: Dict[str, Any] = Field(default_factory=dict)
    trace: Dict[str, Any] = Field(default_factory=dict)


class SocAnalysisResult(BaseModel):
    summary: Optional[str] = None
    defender: str
    hunter: HunterSection
    judge: JudgeVerdict
    investigation_questions: List[InvestigationQuestionItem] = Field(
        default_factory=list,
        description="SOC follow-up questions each with runnable SPL; empty when verdict is false-positive-like.",
    )
    enrichment: EnrichmentResult
    risk_context: str
    inventory_user: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Resolved inventory user row at analysis time (for UI enrichment).",
    )
    inventory_asset: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Resolved inventory asset row at analysis time (for UI enrichment).",
    )
    framework_mapping: List[FrameworkMappingItem] = Field(default_factory=list)
    evidence_refs: List[str] = Field(default_factory=list)
    triage: Optional[TriageOutcome] = Field(
        default=None,
        description="Post-analysis priority and review verdict for analyst queue.",
    )
    threat_intel: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Compact threat-intel findings (malicious/suspicious IOCs) used in SOC analysis.",
    )
    similar_alert_context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Similar past alerts (essential fields) from RAG retrieval.",
    )
    admin_org_gap: Optional[AdminOrgGapSuggestResponse] = Field(
        default=None,
        description="Organizational knowledge gap: optional one question for an administrator.",
    )
    evidence_chain: Optional[EvidenceChain] = Field(
        default=None,
        description="Structured evidence lineage from alert context to Judge verdict.",
    )


class AnalysisRunRequest(BaseModel):
    """Run Hunter / Defender / Judge on a normalized alert + optional Splunk context."""

    normalized: Dict[str, Any] = Field(default_factory=dict)
    search_name: Optional[str] = None
    sid: Optional[str] = None
    row_index: Optional[int] = Field(
        default=None,
        ge=0,
        description="Splunk result row to analyze (default 0). Stored in PostgreSQL audit rows.",
    )
    splunk_results: List[Dict[str, Any]] = Field(default_factory=list)

    enrichment: Optional[EnrichmentResult] = None
    users: Optional[List[Dict[str, Any]]] = None
    assets: Optional[List[Dict[str, Any]]] = None
    relationships: Optional[List[Dict[str, Any]]] = None


class AnalysisBatchBySidRequest(BaseModel):
    """
    Fetch all Splunk job results for ``sid`` via REST, then run SOC analysis once per result row.

    ``normalized`` is merged with each row (row keys override) to build per-row enrichment context.
    """

    sid: str
    search_name: Optional[str] = None
    normalized: Dict[str, Any] = Field(default_factory=dict)
    users: Optional[List[Dict[str, Any]]] = None
    assets: Optional[List[Dict[str, Any]]] = None
    relationships: Optional[List[Dict[str, Any]]] = None
    max_rows: int = Field(100, ge=1, le=500, description="Cap rows analyzed per request (LLM cost / timeout).")
    stop_on_first_error: bool = Field(
        False,
        description="If true, abort the batch when one row analysis raises; otherwise record error per row.",
    )


class RowAnalysisOutcome(BaseModel):
    """One Splunk result row index and the corresponding analysis result or error."""

    row_index: int
    ok: bool
    error: Optional[str] = None
    result: Optional[SocAnalysisResult] = None


class AnalysisBatchBySidResponse(BaseModel):
    """Aggregated per-row analysis for a single Splunk search job (``sid``)."""

    sid: str
    search_name: Optional[str] = None
    splunk_results_row_count: int = Field(description="Total rows returned for this job from Splunk REST.")
    analyzed_row_count: int = Field(description="Number of rows processed in this batch (after ``max_rows`` cap).")
    rows: List[RowAnalysisOutcome] = Field(default_factory=list)
