"""Compact RAG document from persisted SOC analysis."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from models.analysis import SocAnalysisResult

from .compact_alert import (
    _build_chunk_text,
    _build_summary_line,
    extract_essential_fields,
    make_doc_id,
)
from .models import RagAlertDocument


def _inventory_lines(
    inventory_user: Optional[Dict[str, Any]],
    inventory_asset: Optional[Dict[str, Any]],
) -> List[str]:
    lines: List[str] = []
    if inventory_user:
        lines.append("Matched inventory user: {0}".format(json.dumps(inventory_user, default=str)[:500]))
    if inventory_asset:
        lines.append("Matched inventory asset: {0}".format(json.dumps(inventory_asset, default=str)[:500]))
    return lines


def _rich_analysis_extra_lines(
    result: SocAnalysisResult,
    *,
    inventory_user: Optional[Dict[str, Any]] = None,
    inventory_asset: Optional[Dict[str, Any]] = None,
) -> List[str]:
    judge = result.judge
    extra = [
        "Verdict: {0}".format(judge.verdict or ""),
        "Priority: {0}".format(judge.priority or ""),
        "Next step: {0}".format((judge.recommended_next_step or "")[:300]),
        "Judge rationale: {0}".format((judge.rationale or "")[:400]),
    ]
    if result.summary:
        extra.append("Analysis summary: {0}".format((result.summary or "")[:400]))
    if result.defender:
        extra.append("Defender: {0}".format(str(result.defender)[:600]))
    if result.hunter and result.hunter.narrative:
        extra.append("Hunter: {0}".format(result.hunter.narrative[:600])
        )
    if result.hunter and result.hunter.splunk_search_suggestions:
        extra.append(
            "Hunter SPL ideas: {0}".format("; ".join(result.hunter.splunk_search_suggestions[:5])[:400])
        )
    if result.risk_context:
        extra.append("Risk context: {0}".format(str(result.risk_context)[:500])
        )
    if result.enrichment and result.enrichment.notes:
        extra.append("Enrichment: {0}".format(str(result.enrichment.notes)[:300])
        )
    if result.triage:
        extra.append(
            "Triage: score={0} review={1} priority={2}".format(
                result.triage.triage_score,
                result.triage.review_verdict,
                result.triage.investigation_priority,
            )
        )
    for m in (result.framework_mapping or [])[:5]:
        extra.append("MITRE {0}: {1} {2}".format(m.id, m.name, m.confidence))
    if result.threat_intel:
        extra.append("Threat intel: {0}".format(json.dumps(result.threat_intel, default=str)[:500])
        )
    for iq in (result.investigation_questions or [])[:4]:
        extra.append("Investigation Q: {0} | SPL: {1}".format(iq.question[:200], iq.spl[:200]))
    if result.admin_org_gap and result.admin_org_gap.should_suggest_question:
        extra.append("Admin org gap Q: {0}".format((result.admin_org_gap.question_for_admin or "")[:300])
        )
    extra.extend(_inventory_lines(inventory_user, inventory_asset))
    return extra


def compact_analysis_document(
    *,
    sid: Optional[str],
    search_name: Optional[str],
    normalized: Dict[str, Any],
    result: SocAnalysisResult,
    row_index: int = 0,
    inventory_user: Optional[Dict[str, Any]] = None,
    inventory_asset: Optional[Dict[str, Any]] = None,
) -> RagAlertDocument:
    essential = extract_essential_fields(normalized or {})
    judge = result.judge
    verdict = (judge.verdict or "").strip()
    priority = (judge.priority or "").strip()
    essential["verdict"] = verdict
    essential["priority"] = priority
    summary_line = _build_summary_line(search_name, essential)
    if result.summary:
        summary_line = "{0} | {1}".format(summary_line, (result.summary or "")[:200])
    extra = _rich_analysis_extra_lines(
        result,
        inventory_user=inventory_user,
        inventory_asset=inventory_asset,
    )
    chunk_text = _build_chunk_text(
        doc_type="soc_analysis",
        sid=sid,
        search_name=search_name,
        essential=essential,
        extra_lines=extra,
    )
    doc_id = make_doc_id(sid, row_index, "soc_analysis")
    meta: Dict[str, Any] = {
        "sid": sid,
        "search_name": search_name,
        "row_index": row_index,
        "doc_type": "soc_analysis",
        "verdict": verdict,
        "priority": priority,
        "track": "security",
    }
    for k, v in essential.items():
        meta[k] = v
    return RagAlertDocument(
        doc_type="soc_analysis",
        doc_id=doc_id,
        sid=sid,
        search_name=search_name,
        row_index=row_index,
        essential=essential,
        summary_line=summary_line,
        chunk_text=chunk_text,
        metadata=meta,
    )


def compact_analysis_from_payload(payload: Dict[str, Any]) -> Optional[RagAlertDocument]:
    """Build analysis doc from stored tsoc_records payload."""
    sid = payload.get("sid")
    search_name = payload.get("search_name")
    row_index = int(payload.get("row_index") or 0)
    raw = payload.get("raw_alert") if isinstance(payload.get("raw_alert"), dict) else {}
    normalized = raw.get("normalized") if isinstance(raw.get("normalized"), dict) else {}
    if not normalized and isinstance(payload.get("normalized"), dict):
        normalized = payload["normalized"]
    analysis = payload.get("analysis") if isinstance(payload.get("analysis"), dict) else payload
    inv_user = payload.get("inventory_user")
    inv_asset = payload.get("inventory_asset")
    if not isinstance(inv_user, dict):
        inp = payload.get("analysis_input") if isinstance(payload.get("analysis_input"), dict) else {}
        inv_user = inp.get("inventory_user") if isinstance(inp.get("inventory_user"), dict) else None
    if not isinstance(inv_asset, dict):
        inp = payload.get("analysis_input") if isinstance(payload.get("analysis_input"), dict) else {}
        inv_asset = inp.get("inventory_asset") if isinstance(inp.get("inventory_asset"), dict) else None
    try:
        result = SocAnalysisResult.model_validate(analysis)
    except Exception:
        judge = analysis.get("judge") if isinstance(analysis.get("judge"), dict) else {}
        if not judge:
            return None
        from models.analysis import HunterSection, JudgeVerdict

        from models.enrichment import EnrichmentResult

        enr_raw = analysis.get("enrichment")
        if isinstance(enr_raw, dict):
            enrichment = EnrichmentResult.model_validate(enr_raw)
        else:
            enrichment = EnrichmentResult(confidence="low", notes="backfill")
        result = SocAnalysisResult(
            summary=analysis.get("summary"),
            defender=str(analysis.get("defender") or ""),
            hunter=HunterSection.model_validate(analysis.get("hunter") or {"narrative": ""}),
            judge=JudgeVerdict.model_validate(judge),
            enrichment=enrichment,
            risk_context=str(analysis.get("risk_context") or ""),
        )
    return compact_analysis_document(
        sid=sid if isinstance(sid, str) else None,
        search_name=search_name if isinstance(search_name, str) else None,
        normalized=normalized,
        result=result,
        row_index=row_index,
        inventory_user=inv_user if isinstance(inv_user, dict) else None,
        inventory_asset=inv_asset if isinstance(inv_asset, dict) else None,
    )
