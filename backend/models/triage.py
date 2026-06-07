"""Post-analysis triage outcome (priority queue, DeeperSplunk-inspired verdicts)."""

from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field

ReviewVerdict = Literal["TRUE_POSITIVE", "FALSE_POSITIVE", "NEEDS_HUMAN_REVIEW"]
InvestigationPriority = Literal["critical", "high", "medium", "low"]
SourceTrack = Literal["security", "observability"]


class TriageFactor(BaseModel):
    """One line in the triage report explaining a scoring or escalation input."""

    title: str
    explanation: str
    score_impact: Optional[int] = Field(
        default=None,
        description="Points added or subtracted from triage_score (negative = penalty).",
    )


class TriageReport(BaseModel):
    """Human-readable triage report for Investigation UI."""

    headline: str = Field(description="One-sentence summary for the analyst.")
    why_verdict: str = Field(description="Why this review_verdict was chosen.")
    why_priority: str = Field(description="Why this investigation_priority / score.")
    recommended_action: str = Field(description="What the analyst should do next.")
    factors: List[TriageFactor] = Field(default_factory=list)
    signal_notes: List[str] = Field(
        default_factory=list,
        description="Plain-language notes for each triage signal flag.",
    )


class TriageOutcome(BaseModel):
    review_verdict: ReviewVerdict
    investigation_priority: InvestigationPriority
    triage_score: int = Field(ge=0, le=100, description="Sort key for analyst queue (higher = review sooner).")
    confidence_score: float = Field(ge=0.0, le=1.0)
    priority_rationale: str
    signals: List[str] = Field(default_factory=list)
    needs_human_review: bool
    source_track: SourceTrack
    mapped_from: Dict[str, str] = Field(
        default_factory=dict,
        description="Traceability, e.g. judge.verdict → review_verdict.",
    )
    report: Optional[TriageReport] = Field(
        default=None,
        description="Structured analyst report (headline, reasons, recommended action).",
    )
