"""Compute post-analysis triage priority from Judge/Ops outputs."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from models.agentic_ops import AlertClassificationResult
from models.analysis import JudgeVerdict, SocAnalysisResult
from models.enrichment import EnrichmentResult
from models.observability import ObservabilityAnalysisResult, OpsJudgeVerdict
from models.triage import InvestigationPriority, ReviewVerdict, TriageFactor, TriageOutcome, TriageReport
from services.soc_analysis.soc_verdict import verdict_implies_false_positive

CONVICTION_CONFIDENCE_THRESHOLD = 0.75

_TRUE_POSITIVE_LIKE = frozenset(
    {
        "true_positive",
        "confirmed",
        "confirmed_malicious",
        "malicious",
        "threat",
        "attack",
        "compromised",
        "active_threat",
    }
)


def _norm_token(value: str) -> str:
    v = (value or "").strip().lower().replace(" ", "_").replace("-", "_")
    while "__" in v:
        v = v.replace("__", "_")
    return v


def map_judge_verdict_to_review(verdict: str) -> ReviewVerdict:
    """Map free-form Judge verdict to closed review taxonomy."""
    if verdict_implies_false_positive(verdict):
        return "FALSE_POSITIVE"
    n = _norm_token(verdict)
    if n in _TRUE_POSITIVE_LIKE:
        return "TRUE_POSITIVE"
    for token in _TRUE_POSITIVE_LIKE:
        if token in n:
            return "TRUE_POSITIVE"
    return "NEEDS_HUMAN_REVIEW"


def confidence_to_score(confidence: Optional[str]) -> float:
    c = _norm_token(confidence or "")
    if c == "high":
        return 0.85
    if c == "medium":
        return 0.65
    if c == "low":
        return 0.40
    return 0.55


def _priority_weight(priority: str) -> int:
    p = _norm_token(priority)
    if "critical" in p:
        return 15
    if "high" in p:
        return 10
    if "medium" in p:
        return 5
    return 0


def _impact_weight(impact_level: Optional[str]) -> int:
    level = _norm_token(impact_level or "")
    if level == "critical":
        return 15
    if level == "high":
        return 10
    if level == "medium":
        return 5
    return 0


def _inventory_risk_bonus(
    user_row: Optional[Dict[str, Any]],
    asset_row: Optional[Dict[str, Any]],
) -> int:
    scores: List[int] = []
    for row in (user_row, asset_row):
        if not row:
            continue
        raw = row.get("risk_score")
        try:
            scores.append(int(raw))
        except (TypeError, ValueError):
            continue
    if not scores:
        return 0
    return min(max(scores), 10)


def _enrichment_penalty(enrichment: Optional[EnrichmentResult]) -> int:
    if enrichment is None:
        return 5
    conf = enrichment.confidence
    if conf == "low":
        return 10
    if conf == "medium":
        return 5
    return 0


def investigation_priority_from_score(score: int) -> InvestigationPriority:
    if score >= 80:
        return "critical"
    if score >= 60:
        return "high"
    if score >= 40:
        return "medium"
    return "low"


def _base_score_for_review(review: ReviewVerdict) -> int:
    if review == "TRUE_POSITIVE":
        return 75
    if review == "NEEDS_HUMAN_REVIEW":
        return 55
    return 15


def _apply_conviction_gate(
    review: ReviewVerdict,
    confidence_score: float,
) -> ReviewVerdict:
    if review in ("TRUE_POSITIVE", "FALSE_POSITIVE") and confidence_score < CONVICTION_CONFIDENCE_THRESHOLD:
        return "NEEDS_HUMAN_REVIEW"
    return review


_SIGNAL_NOTES: Dict[str, str] = {
    "low_confidence_conviction_gate": (
        "The Judge suggested a firm true/false positive, but confidence was below 0.75 — "
        "automatic closure is not allowed; a human must confirm."
    ),
    "classifier_needs_human_routing": (
        "The alert router could not confidently choose Security vs Observability — "
        "routing ambiguity increases review urgency."
    ),
    "classifier_manual_review": (
        "Classification returned manual_review — an operator must pick the correct pipeline."
    ),
    "weak_enrichment_link": (
        "Asset/user identity linkage is weak — risk context and blast radius are less certain."
    ),
}


def _recommended_action(
    review: ReviewVerdict,
    inv_priority: InvestigationPriority,
    *,
    needs_human: bool,
    judge_next_step: str = "",
) -> str:
    if judge_next_step and judge_next_step.strip():
        prefix = judge_next_step.strip()
    else:
        prefix = ""
    if review == "FALSE_POSITIVE" and inv_priority in ("low", "medium"):
        action = "Document closure as benign/noise; optional spot-check within 24 hours."
    elif review == "TRUE_POSITIVE" and inv_priority == "critical":
        action = "Treat as urgent: validate containment steps, preserve evidence, escalate per runbook."
    elif review == "TRUE_POSITIVE":
        action = "Prioritize investigation: confirm attack chain, contain affected entities, hunt for spread."
    elif needs_human:
        action = "Human review required before disposition — do not auto-close."
    else:
        action = "Continue investigation using Hunter/Judge outputs and suggested SPL."
    if prefix:
        return "{0} Judge recommended: {1}".format(action, prefix)
    return action


def _why_verdict_text(
    review: ReviewVerdict,
    raw_review: ReviewVerdict,
    verdict: str,
    confidence_score: float,
) -> str:
    if review != raw_review:
        return (
            "Initial mapping from Judge verdict '{0}' was {1}, but confidence ({2:.0%}) is below the "
            "0.75 conviction threshold — escalated to NEEDS_HUMAN_REVIEW so the SOC does not "
            "auto-convict or auto-acquit on uncertain evidence."
        ).format(verdict, raw_review, confidence_score)
    if review == "FALSE_POSITIVE":
        return (
            "Judge verdict '{0}' maps to a benign/false-positive class. Evidence was treated as "
            "insufficient to justify active incident response."
        ).format(verdict)
    if review == "TRUE_POSITIVE":
        return (
            "Judge verdict '{0}' indicates malicious or confirmed-threat activity with sufficient "
            "confidence (≥0.75) for a true-positive disposition."
        ).format(verdict)
    return (
        "Judge verdict '{0}' is inconclusive, mixed, or needs_more_evidence — defaulting to "
        "NEEDS_HUMAN_REVIEW until an analyst validates the story."
    ).format(verdict)


def _why_priority_text(
    inv_priority: InvestigationPriority,
    score: int,
    review: ReviewVerdict,
) -> str:
    return (
        "Triage score {0}/100 places this alert in the '{1}' band. "
        "{2} verdicts with higher Judge priority, inventory risk, and routing ambiguity "
        "score higher in the analyst queue."
    ).format(score, inv_priority, review.replace("_", " "))


def _build_triage_report(
    *,
    review: ReviewVerdict,
    raw_review: ReviewVerdict,
    verdict: str,
    priority: str,
    confidence: Optional[str],
    confidence_score: float,
    inv_priority: InvestigationPriority,
    score: int,
    signals: List[str],
    factors: List[TriageFactor],
    needs_human: bool,
    judge_rationale: str = "",
    judge_next_step: str = "",
) -> TriageReport:
    headline_parts: List[str] = []
    if inv_priority in ("critical", "high"):
        headline_parts.append("{0} priority".format(inv_priority.upper()))
    headline_parts.append(review.replace("_", " "))
    headline_parts.append("score {0}".format(score))
    headline = " — ".join(headline_parts) + "."

    signal_notes = [_SIGNAL_NOTES[s] for s in signals if s in _SIGNAL_NOTES]

    return TriageReport(
        headline=headline,
        why_verdict=_why_verdict_text(review, raw_review, verdict, confidence_score),
        why_priority=_why_priority_text(inv_priority, score, review),
        recommended_action=_recommended_action(
            review,
            inv_priority,
            needs_human=needs_human,
            judge_next_step=judge_next_step,
        ),
        factors=factors,
        signal_notes=signal_notes,
    )


def compute_triage_outcome(
    *,
    source_track: str,
    verdict: str,
    priority: str,
    confidence: Optional[str],
    rationale: str = "",
    recommended_next_step: str = "",
    classification: Optional[AlertClassificationResult] = None,
    enrichment: Optional[EnrichmentResult] = None,
    user_row: Optional[Dict[str, Any]] = None,
    asset_row: Optional[Dict[str, Any]] = None,
    impact_level: Optional[str] = None,
) -> TriageOutcome:
    """Score analyst review priority from Judge/Ops outputs and context."""
    raw_review = map_judge_verdict_to_review(verdict)
    confidence_score = confidence_to_score(confidence)
    review = _apply_conviction_gate(raw_review, confidence_score)

    signals: List[str] = []
    factors: List[TriageFactor] = []

    factors.append(
        TriageFactor(
            title="Judge verdict",
            explanation="Original verdict '{0}' mapped to {1}.".format(verdict, raw_review),
            score_impact=None,
        )
    )

    if review != raw_review:
        signals.append("low_confidence_conviction_gate")
        factors.append(
            TriageFactor(
                title="Conviction gate",
                explanation="Confidence {0:.0%} is below 0.75 — verdict raised to NEEDS_HUMAN_REVIEW.".format(
                    confidence_score
                ),
                score_impact=None,
            )
        )

    base = _base_score_for_review(review)
    factors.append(
        TriageFactor(
            title="Review class base",
            explanation="Base queue weight for {0}.".format(review.replace("_", " ")),
            score_impact=base,
        )
    )
    score = base

    pw = _priority_weight(priority)
    if pw:
        factors.append(
            TriageFactor(
                title="Judge priority",
                explanation="Judge marked priority '{0}'.".format(priority),
                score_impact=pw,
            )
        )
    score += pw

    risk_bonus = _inventory_risk_bonus(user_row, asset_row)
    if risk_bonus:
        factors.append(
            TriageFactor(
                title="Inventory risk",
                explanation="Elevated user/asset risk_score from inventory.",
                score_impact=risk_bonus,
            )
        )
    score += risk_bonus

    impact_w = _impact_weight(impact_level)
    if impact_w:
        factors.append(
            TriageFactor(
                title="Operational impact",
                explanation="Impact level '{0}'.".format(impact_level or ""),
                score_impact=impact_w,
            )
        )
    score += impact_w

    id_penalty = _enrichment_penalty(enrichment)
    if id_penalty:
        if enrichment and enrichment.confidence == "low":
            signals.append("weak_enrichment_link")
        factors.append(
            TriageFactor(
                title="Enrichment confidence",
                explanation="Penalty for weak or missing inventory linkage.",
                score_impact=-id_penalty,
            )
        )
    score -= id_penalty

    if classification and classification.needs_human_routing:
        signals.append("classifier_needs_human_routing")
        factors.append(
            TriageFactor(
                title="Router ambiguity",
                explanation=classification.reason[:200] if classification.reason else "Needs human routing.",
                score_impact=12,
            )
        )
        score += 12
    if classification and classification.recommended_pipeline == "manual_review":
        signals.append("classifier_manual_review")
        factors.append(
            TriageFactor(
                title="Manual routing",
                explanation="Classifier could not auto-select Security vs Observability.",
                score_impact=None,
            )
        )

    if review == "NEEDS_HUMAN_REVIEW":
        factors.append(
            TriageFactor(
                title="Human review default",
                explanation="Inconclusive or escalated verdict — analyst validation required.",
                score_impact=8,
            )
        )
        score += 8

    score = max(0, min(100, score))

    inv_priority = investigation_priority_from_score(score)
    needs_human = review == "NEEDS_HUMAN_REVIEW" or (
        classification is not None and classification.needs_human_routing
    )

    report = _build_triage_report(
        review=review,
        raw_review=raw_review,
        verdict=verdict,
        priority=priority,
        confidence=confidence,
        confidence_score=confidence_score,
        inv_priority=inv_priority,
        score=score,
        signals=signals,
        factors=factors,
        needs_human=needs_human,
        judge_rationale=rationale,
        judge_next_step=recommended_next_step,
    )

    parts: List[str] = [report.headline, report.why_verdict, report.why_priority]
    if rationale:
        parts.append("Judge rationale: {0}".format(rationale[:400]))
    if signals:
        parts.append("Signals: {0}.".format(", ".join(signals)))

    track: str = source_track if source_track in ("security", "observability") else "security"

    return TriageOutcome(
        review_verdict=review,
        investigation_priority=inv_priority,
        triage_score=score,
        confidence_score=confidence_score,
        priority_rationale=" ".join(parts),
        signals=signals,
        needs_human_review=needs_human,
        source_track=track,  # type: ignore[arg-type]
        mapped_from={
            "judge.verdict": verdict,
            "judge.priority": priority,
            "judge.confidence": confidence or "",
            "review_verdict_raw": raw_review,
        },
        report=report,
    )


def compute_triage_from_soc(
    result: SocAnalysisResult,
    *,
    classification: Optional[AlertClassificationResult] = None,
    user_row: Optional[Dict[str, Any]] = None,
    asset_row: Optional[Dict[str, Any]] = None,
) -> TriageOutcome:
    judge = result.judge
    return compute_triage_outcome(
        source_track="security",
        verdict=judge.verdict,
        priority=judge.priority,
        confidence=judge.confidence,
        rationale=judge.rationale,
        recommended_next_step=judge.recommended_next_step,
        classification=classification,
        enrichment=result.enrichment,
        user_row=user_row,
        asset_row=asset_row,
    )


def compute_triage_from_observability(
    result: ObservabilityAnalysisResult,
    *,
    classification: Optional[AlertClassificationResult] = None,
) -> TriageOutcome:
    ops = result.ops_judge
    return compute_triage_outcome(
        source_track="observability",
        verdict=ops.verdict,
        priority=ops.priority,
        confidence=ops.confidence,
        rationale=ops.rationale,
        recommended_next_step=ops.recommended_next_step,
        classification=classification,
        impact_level=result.impact_context.impact_level,
    )


def compute_triage_from_judge_verdict(
    judge: JudgeVerdict,
    *,
    source_track: str = "security",
    classification: Optional[AlertClassificationResult] = None,
    enrichment: Optional[EnrichmentResult] = None,
    user_row: Optional[Dict[str, Any]] = None,
    asset_row: Optional[Dict[str, Any]] = None,
    impact_level: Optional[str] = None,
) -> TriageOutcome:
    return compute_triage_outcome(
        source_track=source_track,
        verdict=judge.verdict,
        priority=judge.priority,
        confidence=judge.confidence,
        rationale=judge.rationale,
        recommended_next_step=judge.recommended_next_step,
        classification=classification,
        enrichment=enrichment,
        user_row=user_row,
        asset_row=asset_row,
        impact_level=impact_level,
    )


def compute_triage_from_ops_judge(
    ops: OpsJudgeVerdict,
    *,
    classification: Optional[AlertClassificationResult] = None,
    impact_level: Optional[str] = None,
) -> TriageOutcome:
    return compute_triage_outcome(
        source_track="observability",
        verdict=ops.verdict,
        priority=ops.priority,
        confidence=ops.confidence,
        rationale=ops.rationale,
        recommended_next_step=ops.recommended_next_step,
        classification=classification,
        impact_level=impact_level,
    )


def triage_from_stored_payload(payload: Dict[str, Any]) -> Optional[TriageOutcome]:
    """Read embedded triage or recompute from stored analysis for queue API."""
    if not isinstance(payload, dict):
        return None
    raw = payload.get("triage")
    if isinstance(raw, dict):
        try:
            return TriageOutcome.model_validate(raw)
        except Exception:
            pass
    analysis = payload.get("analysis")
    if isinstance(analysis, dict):
        nested = analysis.get("triage")
        if isinstance(nested, dict):
            try:
                return TriageOutcome.model_validate(nested)
            except Exception:
                pass
        record_type = payload.get("tsoc_record_type") or ""
        try:
            if record_type == "observability_analysis":
                obs = ObservabilityAnalysisResult.model_validate(analysis)
                return compute_triage_from_observability(obs)
            soc = SocAnalysisResult.model_validate(analysis)
            return compute_triage_from_soc(soc)
        except Exception:
            judge_raw = analysis.get("judge") or analysis.get("ops_judge")
            if isinstance(judge_raw, dict):
                verdict = str(judge_raw.get("verdict") or "")
                priority = str(judge_raw.get("priority") or "medium")
                confidence = judge_raw.get("confidence")
                track = "observability" if "ops_judge" in analysis or record_type == "observability_analysis" else "security"
                impact = None
                ic = analysis.get("impact_context")
                if isinstance(ic, dict):
                    impact = ic.get("impact_level")
                return compute_triage_outcome(
                    source_track=track,
                    verdict=verdict,
                    priority=priority,
                    confidence=str(confidence) if confidence is not None else None,
                    rationale=str(judge_raw.get("rationale") or ""),
                    recommended_next_step=str(judge_raw.get("recommended_next_step") or ""),
                    impact_level=str(impact) if impact else None,
                )
    return None


def merge_triage_into_analysis_output(
    analysis_output: Dict[str, Any],
    triage: TriageOutcome,
) -> Dict[str, Any]:
    out = dict(analysis_output)
    td = triage.model_dump(mode="json")
    out["triage"] = td
    out["review_verdict"] = td["review_verdict"]
    out["investigation_priority"] = td["investigation_priority"]
    out["triage_score"] = td["triage_score"]
    out["needs_human_review"] = td["needs_human_review"]
    return out
