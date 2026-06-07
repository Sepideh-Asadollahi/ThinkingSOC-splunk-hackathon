"""Map LangGraph final state + request body to ``SocAnalysisResult``."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from models.analysis import (
    AnalysisRunRequest,
    FrameworkMappingItem,
    HunterSection,
    JudgeVerdict,
    SocAnalysisResult,
)
from models.enrichment import EnrichmentResult
from models.mcp import McpHunterEvidence, McpJudgeEvidence
from services.soc_analysis.framework_mapping import ensure_mitre_and_kill_chain, parse_framework_mapping_items
from services.investigation.investigation_questions_spl import finalize_investigation_questions_for_verdict
from services.threat_intel.threat_intel_compact import compact_threat_intel_for_analysis

from services.investigation.spl_predict_pipeline import strip_time_range_from_spl

from .evidence import build_evidence_refs


def _parse_hunter_mcp(raw: Any) -> Optional[McpHunterEvidence]:
    if isinstance(raw, dict) and raw:
        try:
            return McpHunterEvidence.model_validate(raw)
        except Exception:
            return None
    return None


def _parse_judge_mcp(raw: Any) -> Optional[McpJudgeEvidence]:
    if isinstance(raw, dict) and raw:
        try:
            return McpJudgeEvidence.model_validate(raw)
        except Exception:
            return None
    return None


async def assemble_from_langgraph(
    final_state: Dict[str, Any],
    enrichment: EnrichmentResult,
    body: AnalysisRunRequest,
    settings,
) -> SocAnalysisResult:
    """Map LangGraph outputs + prepare state to API contract."""
    risk_context = str(final_state.get("risk_context") or "")
    d_def = final_state.get("defender_output") or {}
    d_hunt = final_state.get("hunter_output") or {}
    d_j = final_state.get("judge_output") or {}

    defender_str = str(d_def.get("defender") or "")

    sug = d_hunt.get("splunk_search_suggestions") or []
    if isinstance(sug, str):
        sug = [sug]
    if not sug:
        sug = ["index=* | head 50"]
    hunter = HunterSection(
        narrative=str(d_hunt.get("narrative") or ""),
        splunk_search_suggestions=[
            strip_time_range_from_spl(str(x)) for x in sug if str(x).strip()
        ],
        mcp_evidence=_parse_hunter_mcp(final_state.get("hunter_mcp_context")),
    )

    j = d_j.get("judge") or {}
    judge = JudgeVerdict(
        verdict=str(j.get("verdict") or "unknown"),
        priority=str(j.get("priority") or "medium"),
        recommended_next_step=str(j.get("recommended_next_step") or j.get("next_step") or ""),
        rationale=str(j.get("rationale") or ""),
        confidence=j.get("confidence") if j.get("confidence") in ("high", "medium", "low") else None,
        mcp_evidence=_parse_judge_mcp(final_state.get("judge_mcp_context")),
    )

    d_inv = final_state.get("investigation_questions_output") or {}
    legacy_rc = final_state.get("root_cause_spl_output")
    inv_q = await finalize_investigation_questions_for_verdict(
        settings,
        judge.verdict,
        d_inv.get("investigation_questions"),
        legacy_root_spl=legacy_rc,
        normalized=body.normalized,
        search_name=body.search_name or "",
        sid=body.sid,
        splunk_results=list(body.splunk_results or []),
        canonical_prefix=str(final_state.get("canonical_prefix") or ""),
        defender_output=d_def,
        hunter_output=d_hunt,
        judge_output=d_j,
    )

    d_fw = final_state.get("framework_mapping_output") or {}
    fw_list = ensure_mitre_and_kill_chain(
        parse_framework_mapping_items(d_fw.get("framework_mapping")),
        normalized=body.normalized,
    )

    summary_val = d_j.get("summary")
    summary_out: Optional[str] = str(summary_val) if summary_val is not None else None

    ti_raw = final_state.get("threat_intel")
    threat_intel: Optional[Dict[str, Any]] = None
    if isinstance(ti_raw, dict) and ti_raw:
        threat_intel = compact_threat_intel_for_analysis(ti_raw) or ti_raw

    sim_raw = final_state.get("similar_alert_context")
    similar_alert_context = sim_raw if isinstance(sim_raw, dict) and sim_raw else None

    return SocAnalysisResult(
        summary=summary_out,
        defender=defender_str,
        hunter=hunter,
        judge=judge,
        investigation_questions=inv_q,
        enrichment=enrichment,
        risk_context=risk_context,
        framework_mapping=fw_list,
        evidence_refs=build_evidence_refs(body.normalized, body.splunk_results),
        threat_intel=threat_intel,
        similar_alert_context=similar_alert_context,
    )
