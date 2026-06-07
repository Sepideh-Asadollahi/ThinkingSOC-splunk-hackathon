"""Deterministic SOC analysis result when LLM is disabled or the graph fails."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from models.analysis import (
    FrameworkMappingItem,
    HunterSection,
    JudgeVerdict,
    SocAnalysisResult,
)
from models.enrichment import EnrichmentResult
from services.soc_analysis.framework_mapping import default_dual_framework_fallback
from services.investigation.investigation_question_context import postprocess_investigation_question_strings
from services.investigation.investigation_questions_spl import investigation_questions_for_verdict

from .evidence import build_evidence_refs
from .fallback_questions import fallback_investigation_questions
from .text import truncate


def build_fallback_soc_result(
    enrichment: EnrichmentResult,
    risk_context: str,
    normalized: Dict[str, Any],
    search_name: Optional[str],
    splunk_results: List[Dict[str, Any]],
) -> SocAnalysisResult:
    host = truncate(normalized.get("host") or normalized.get("dest") or "unknown")
    user = truncate(normalized.get("user") or "unknown")
    sn = search_name or "alert"

    defender = (
        "- Alternate: alert `{0}` may reflect routine activity on `{1}` for `{2}` without attack chain in context.\n"
        "- Weak signal: rule-based fallback has no corroborating events in payload.\n"
        "- Minimal check: confirm change/deployment record for the process and parent before escalation.\n"
        "- Would treat as incident if: auth anomalies, egress, or persistence appear in follow-up searches.".format(
            sn, host, user
        )
    )

    sug = [
        'index=* host="{0}" | stats count by source, sourcetype'.format(host.replace('"', "")),
        'index=* user="{0}" OR src_user="{0}" | head 100'.format(str(user).replace('"', "")),
    ]
    hunter = HunterSection(
        narrative=(
            "Expand around the same time window: authentication, process, and network edges involving the same host/user. "
            "Correlate with proxy and EDR if available."
        ),
        splunk_search_suggestions=sug,
    )

    judge = JudgeVerdict(
        verdict="needs_investigation",
        priority="medium",
        recommended_next_step="Triage in SIEM: confirm enrichment, review risk_context, then escalate if corroborated.",
        rationale=(
            "Rule-based fallback (no LLM). Consider risk_context: {0} Identity: {1}".format(
                risk_context[:400],
                enrichment.notes[:200],
            )
        ),
        confidence="low",
    )

    from config import Settings, investigation_questions_max

    cfg = Settings()
    max_q = investigation_questions_max(cfg)
    raw_qs = postprocess_investigation_question_strings(
        fallback_investigation_questions(normalized, splunk_results, max_items=max_q),
        normalized=normalized,
        splunk_results=splunk_results,
        search_name=search_name or "",
        max_items=max_q,
    )
    inv_q = investigation_questions_for_verdict(
        judge.verdict,
        [{"question": q} for q in raw_qs],
        settings=cfg,
        normalized=normalized,
    )

    fw = default_dual_framework_fallback()

    return SocAnalysisResult(
        summary=judge.rationale[:500],
        defender=defender,
        hunter=hunter,
        judge=judge,
        investigation_questions=inv_q,
        enrichment=enrichment,
        risk_context=risk_context,
        framework_mapping=fw,
        evidence_refs=build_evidence_refs(normalized, splunk_results),
    )
