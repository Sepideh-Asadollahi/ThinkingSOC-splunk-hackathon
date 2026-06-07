"""Persist SOC analysis, audit, investigation phases, and batch summaries."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from config import Settings
from models.analysis import AnalysisBatchBySidResponse, AnalysisRunRequest, SocAnalysisResult

from .. import pg
from ._common import stored_at_iso


async def persist_soc_analysis_to_splunk(
    settings: Settings,
    body: AnalysisRunRequest,
    result: SocAnalysisResult,
    *,
    row_index: Optional[int] = None,
    raw_alert: Optional[Dict[str, Any]] = None,
    analysis_input: Optional[Dict[str, Any]] = None,
    analysis_output: Optional[Dict[str, Any]] = None,
) -> None:
    if not pg.splunk_store_configured(settings):
        return
    from services.soc_analysis.analysis_audit import resolve_row_index

    idx = resolve_row_index(row_index, body.splunk_results)
    triage_dump = result.triage.model_dump(mode="json") if result.triage else None
    payload: Dict[str, Any] = {
        "tsoc_record_type": "soc_analysis",
        "stored_at": stored_at_iso(),
        "sid": body.sid,
        "search_name": body.search_name,
        "row_index": idx,
        "raw_alert": raw_alert,
        "analysis_input": analysis_input,
        "analysis_output": analysis_output,
        "analysis": result.model_dump(mode="json"),
    }
    if triage_dump is not None:
        payload["triage"] = triage_dump
    await pg.submit_hec_event(settings, payload)


async def persist_soc_analysis_audit(
    settings: Settings,
    *,
    sid: Optional[str],
    search_name: Optional[str],
    row_index: int,
    raw_alert: Dict[str, Any],
    analysis_input: Dict[str, Any],
    analysis_output: Optional[Dict[str, Any]],
) -> None:
    if not pg.splunk_store_configured(settings):
        return
    payload: Dict[str, Any] = {
        "tsoc_record_type": "soc_analysis_audit",
        "stored_at": stored_at_iso(),
        "sid": sid,
        "search_name": search_name,
        "row_index": row_index,
        "raw_alert": raw_alert,
        "analysis_input": analysis_input,
        "analysis_output": analysis_output,
    }
    await pg.submit_hec_event(settings, payload)


async def persist_soc_investigation_phases(
    settings: Settings,
    body: AnalysisRunRequest,
    result: SocAnalysisResult,
    *,
    row_index: Optional[int] = None,
    raw_alert: Optional[Dict[str, Any]] = None,
    analysis_input: Optional[Dict[str, Any]] = None,
    analysis_output: Optional[Dict[str, Any]] = None,
) -> None:
    if not pg.splunk_store_configured(settings):
        return
    from services.soc_analysis.analysis_audit import (
        build_analysis_input,
        build_analysis_output,
        build_raw_alert,
        resolve_row_index,
    )

    idx = resolve_row_index(row_index, body.splunk_results)
    raw = raw_alert or build_raw_alert(
        sid=body.sid,
        search_name=body.search_name,
        normalized=body.normalized,
        splunk_results=body.splunk_results,
        row_index=idx,
    )
    inp = analysis_input or build_analysis_input(
        search_name=body.search_name,
        normalized=body.normalized,
        splunk_results=body.splunk_results,
        row_index=idx,
    )
    out = analysis_output or build_analysis_output(result)
    alert_fields = inp.get("alert_fields") or {}
    base = {
        "sid": body.sid,
        "search_name": body.search_name,
        "row_index": idx,
        "stored_at": stored_at_iso(),
        "raw_alert": raw,
        "analysis_output": out,
    }
    phases: List[tuple[str, str, Any]] = [
        ("soc_investigation_raw_alert", "raw_alert", raw),
        ("soc_investigation_alert_fields", "alert_fields", alert_fields),
        ("soc_investigation_defender", "defender", result.defender),
        ("soc_investigation_hunter", "hunter", result.hunter.model_dump(mode="json")),
        ("soc_investigation_judge", "judge", result.judge.model_dump(mode="json")),
        (
            "soc_investigation_questions",
            "investigation_questions",
            result.investigation_questions,
        ),
        (
            "soc_investigation_framework",
            "framework_mapping",
            [x.model_dump(mode="json") for x in result.framework_mapping],
        ),
        (
            "soc_investigation_enrichment",
            "enrichment",
            result.enrichment.model_dump(mode="json"),
        ),
        ("soc_investigation_risk", "risk_context", result.risk_context),
    ]
    if result.threat_intel:
        phases.append(
            (
                "soc_investigation_threat_intel",
                "threat_intel",
                result.threat_intel,
            )
        )
    if result.summary:
        phases.append(("soc_investigation_summary", "summary", result.summary))
    if result.evidence_chain:
        phases.append(
            (
                "soc_investigation_evidence_chain",
                "evidence_chain",
                result.evidence_chain.model_dump(mode="json"),
            )
        )
    for rec_type, phase_name, content in phases:
        payload = dict(base)
        payload["tsoc_record_type"] = rec_type
        payload["phase"] = phase_name
        payload["content"] = content
        await pg.submit_hec_event(settings, payload)


async def persist_analysis_batch_summary_to_splunk(
    settings: Settings,
    body_sid: str,
    search_name: Optional[str],
    response: AnalysisBatchBySidResponse,
    *,
    ok_count: int,
    fail_count: int,
) -> None:
    if not pg.splunk_store_configured(settings):
        return
    payload: Dict[str, Any] = {
        "tsoc_record_type": "soc_analysis_batch",
        "stored_at": stored_at_iso(),
        "sid": body_sid,
        "search_name": search_name,
        "splunk_results_row_count": response.splunk_results_row_count,
        "analyzed_row_count": response.analyzed_row_count,
        "rows_ok": ok_count,
        "rows_failed": fail_count,
    }
    await pg.submit_hec_event(settings, payload)
