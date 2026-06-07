"""Final operational verdict for observability pipeline."""

from __future__ import annotations

from models.observability import DiagnoserSection, ImpactContext, OpsJudgeVerdict, ResponderSection


def build_ops_judge(
    impact: ImpactContext,
    diagnoser: DiagnoserSection,
    responder: ResponderSection,
) -> OpsJudgeVerdict:
    first_hyp = diagnoser.root_cause_hypotheses[0] if diagnoser.root_cause_hypotheses else None
    hyp_text = (first_hyp.hypothesis.lower() if first_hyp else "")
    verdict = "needs_more_evidence"
    if "cpu" in hyp_text or "memory" in hyp_text or "disk" in hyp_text:
        verdict = "probable_resource_saturation"
    elif "latency" in hyp_text or "degradation" in hyp_text:
        verdict = "probable_service_degradation"
    elif "dependency" in hyp_text:
        verdict = "probable_dependency_issue"

    priority = "medium"
    if impact.impact_level in ("high", "critical"):
        priority = "high"
    if impact.impact_level == "critical":
        priority = "critical"

    next_step = responder.recommended_actions[0] if responder.recommended_actions else "Collect more correlated metrics/logs."
    confidence = first_hyp.confidence if first_hyp else "low"
    rationale = "Operational verdict derived from impact context and top diagnosis hypothesis."
    if first_hyp:
        rationale = "{0} Hypothesis: {1}".format(rationale, first_hyp.hypothesis)

    escalation = "service owner"
    if impact.business_criticality == "critical":
        escalation = "critical service owner + on-call lead"

    return OpsJudgeVerdict(
        verdict=verdict,
        priority=priority,
        recommended_next_step=next_step,
        confidence=confidence,
        rationale=rationale,
        escalation_target=escalation,
    )
