"""Main SOC analysis entry: enrichment → LangGraph (or fallback) → PostgreSQL store."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from config import Settings
from models.agentic_ops import AlertClassificationResult
from models.analysis import AnalysisRunRequest, EvidenceChain, SocAnalysisResult
from services.soc_analysis.analysis_audit import (
    build_analysis_input,
    build_analysis_output,
    build_raw_alert,
    resolve_row_index,
)
from services.soc_analysis.admin_org_gap import attach_admin_org_gap
from services.alert.enrichment_resolver import enrich_from_inventory
from services.soc_rag import find_similar_alerts, upsert_analysis_document
from services.soc_analysis_graph import SocAnalysisGraphState, run_soc_analysis_langgraph
from services.soc_analysis.soc_analysis_risk import build_risk_context, find_asset_row, find_user_row
from services.soc_analysis.analysis_complete_log import log_analysis_complete
from services.triage.triage_priority import compute_triage_from_soc
from services.splunk_json_store import (
    persist_soc_analysis_audit,
    persist_soc_analysis_to_splunk,
    persist_soc_investigation_phases,
)

from .assembly import assemble_from_langgraph
from .fallback_result import build_fallback_soc_result

logger = logging.getLogger(__name__)


def _preview_rows_for_index(
    splunk_results: List[Dict[str, Any]],
    row_index: int,
) -> List[Dict[str, Any]]:
    if not splunk_results:
        return []
    if 0 <= row_index < len(splunk_results):
        return [splunk_results[row_index]]
    return splunk_results[:5]


def _build_evidence_chain(
    *,
    body: AnalysisRunRequest,
    result: SocAnalysisResult,
    row_index: int,
    raw_alert: Dict[str, Any],
    analysis_input: Dict[str, Any],
    path_name: str,
) -> EvidenceChain:
    questions = list(result.investigation_questions or [])
    executed_ok = 0
    executed_err = 0
    for q in questions:
        spl_results = q.spl_results
        if spl_results is None:
            continue
        if spl_results.error:
            executed_err += 1
        else:
            executed_ok += 1

    return EvidenceChain(
        request={
            "sid": body.sid,
            "search_name": body.search_name,
            "row_index": row_index,
        },
        data_sources={
            "splunk_results_row_count": len(body.splunk_results or ()),
            "selected_result_row_present": bool(raw_alert.get("result_row")),
            "resolved_user_id": result.enrichment.resolved_user_id,
            "resolved_asset_id": result.enrichment.resolved_asset_id,
            "threat_intel_present": bool(result.threat_intel),
            "similar_alert_context_present": bool(result.similar_alert_context),
        },
        reasoning_path={
            "analysis_path": path_name,
            "hunter_mcp_used": bool(result.hunter.mcp_evidence),
            "judge_mcp_used": bool(result.judge.mcp_evidence),
            "investigation_questions_count": len(questions),
            "investigation_spl_executed_ok_count": executed_ok,
            "investigation_spl_error_count": executed_err,
        },
        decision={
            "verdict": result.judge.verdict,
            "priority": result.judge.priority,
            "recommended_next_step": result.judge.recommended_next_step,
            "triage_score": result.triage.triage_score if result.triage else None,
            "investigation_priority": result.triage.investigation_priority if result.triage else None,
            "needs_human_review": result.triage.needs_human_review if result.triage else None,
            "admin_org_gap_suggested": (
                result.admin_org_gap.should_suggest_question if result.admin_org_gap else False
            ),
        },
        trace={
            "evidence_refs_count": len(result.evidence_refs or ()),
            "analysis_input_alert_fields_count": len((analysis_input.get("alert_fields") or {})),
        },
    )


async def _persist_analysis_bundle(
    settings: Settings,
    body: AnalysisRunRequest,
    result: SocAnalysisResult,
    *,
    row_index: int,
    raw_alert: Dict[str, Any],
    analysis_input: Dict[str, Any],
    analysis_output: Dict[str, Any],
) -> None:
    await persist_soc_analysis_to_splunk(
        settings,
        body,
        result,
        row_index=row_index,
        raw_alert=raw_alert,
        analysis_input=analysis_input,
        analysis_output=analysis_output,
    )
    await persist_soc_analysis_audit(
        settings,
        sid=body.sid,
        search_name=body.search_name,
        row_index=row_index,
        raw_alert=raw_alert,
        analysis_input=analysis_input,
        analysis_output=analysis_output,
    )
    await persist_soc_investigation_phases(
        settings,
        body,
        result,
        row_index=row_index,
        raw_alert=raw_alert,
        analysis_input=analysis_input,
        analysis_output=analysis_output,
    )


async def run_analysis(
    settings: Settings,
    body: AnalysisRunRequest,
    *,
    users: List[Dict[str, Any]],
    assets: List[Dict[str, Any]],
    relationships: List[Dict[str, Any]],
    analysis_row_index: Optional[int] = None,
    classification: Optional[AlertClassificationResult] = None,
) -> SocAnalysisResult:
    """
    Enrichment → LangGraph (prepare → risk_engine → Defender → Hunter → Judge) → assemble.

    Inventory tables must already be loaded when calling this function.
    """
    row_index = resolve_row_index(
        analysis_row_index if analysis_row_index is not None else body.row_index,
        body.splunk_results,
    )
    preview_rows = _preview_rows_for_index(body.splunk_results, row_index)
    raw_alert = build_raw_alert(
        sid=body.sid,
        search_name=body.search_name,
        normalized=body.normalized,
        splunk_results=body.splunk_results,
        row_index=row_index,
    )
    analysis_input = build_analysis_input(
        search_name=body.search_name,
        normalized=body.normalized,
        splunk_results=body.splunk_results,
        row_index=row_index,
    )

    enrichment = body.enrichment
    if enrichment is None:
        enrichment = enrich_from_inventory(body.normalized, users, assets, relationships)

    urow = find_user_row(users, enrichment.resolved_user_id)
    arow = find_asset_row(assets, enrichment.resolved_asset_id)
    risk = build_risk_context(enrichment, urow, arow)

    logger.info(
        "soc_analysis enrichment sid=%s search_name=%s row_index=%d user_id=%s asset_id=%s",
        body.sid,
        body.search_name,
        row_index,
        enrichment.resolved_user_id,
        enrichment.resolved_asset_id,
    )

    t0 = time.perf_counter()
    logger.info(
        "soc_analysis start sid=%s search_name=%s row_index=%d splunk_result_rows=%d",
        body.sid,
        body.search_name,
        row_index,
        len(body.splunk_results or ()),
    )

    similar_ctx = await find_similar_alerts(
        settings,
        sid=body.sid,
        search_name=body.search_name,
        normalized=body.normalized,
        splunk_results=body.splunk_results,
        row_index=row_index,
    )

    initial: SocAnalysisGraphState = {
        "normalized": body.normalized,
        "search_name": body.search_name,
        "sid": body.sid,
        "row_index": row_index,
        "splunk_results_preview": preview_rows,
        "enrichment": enrichment.model_dump(),
        "inventory_user": urow,
        "inventory_asset": arow,
        "similar_alert_context": similar_ctx.model_dump(mode="json"),
    }
    try:
        final = await run_soc_analysis_langgraph(settings, initial)
        result = await assemble_from_langgraph(final, enrichment, body, settings)
        path_name = "langgraph"
    except Exception as e:
        logger.warning(
            "SOC LangGraph LLM pipeline failed, using fallback: %s",
            e,
            exc_info=True,
        )
        result = build_fallback_soc_result(
            enrichment, risk, body.normalized, body.search_name, preview_rows
        )
        path_name = "langgraph_fallback"

    triage = compute_triage_from_soc(
        result,
        classification=classification,
        user_row=urow,
        asset_row=arow,
    )
    result = result.model_copy(
        update={
            "triage": triage,
            "similar_alert_context": similar_ctx.model_dump(mode="json"),
            "inventory_user": urow,
            "inventory_asset": arow,
        }
    )
    result = await attach_admin_org_gap(settings, body, result)
    evidence_chain = _build_evidence_chain(
        body=body,
        result=result,
        row_index=row_index,
        raw_alert=raw_alert,
        analysis_input=analysis_input,
        path_name=path_name,
    )
    result = result.model_copy(update={"evidence_chain": evidence_chain})
    analysis_output = build_analysis_output(result)
    await _persist_analysis_bundle(
        settings,
        body,
        result,
        row_index=row_index,
        raw_alert=raw_alert,
        analysis_input=analysis_input,
        analysis_output=analysis_output,
    )
    await upsert_analysis_document(
        settings,
        sid=body.sid,
        search_name=body.search_name,
        normalized=body.normalized,
        result=result,
        row_index=row_index,
        inventory_user=urow,
        inventory_asset=arow,
    )
    duration_ms = (time.perf_counter() - t0) * 1000.0
    gap_flag = (
        result.admin_org_gap.should_suggest_question if result.admin_org_gap else False
    )
    logger.info(
        "soc_analysis done sid=%s row_index=%d verdict=%s priority=%s triage_score=%s "
        "admin_org_gap=%s duration_ms=%.1f",
        body.sid,
        row_index,
        result.judge.verdict,
        result.judge.priority,
        result.triage.triage_score if result.triage else "-",
        gap_flag,
        duration_ms,
    )
    log_analysis_complete(
        pipeline="soc",
        sid=body.sid,
        row_index=row_index,
        verdict=result.judge.verdict,
        priority=result.judge.priority,
        duration_ms=duration_ms,
        extra="{0} triage_score={1} admin_org_gap={2}".format(
            "path={0}".format(path_name),
            result.triage.triage_score if result.triage else "-",
            gap_flag,
        ),
    )
    return result
