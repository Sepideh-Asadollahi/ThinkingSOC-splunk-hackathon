"""Shared agent triage orchestration (used by API and background ingest)."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from config import Settings
from models.agentic_ops import AlertClassificationResult
from models.agents import AgentTriageRequest, AgentTriageResponse
from models.analysis import AnalysisRunRequest
from models.assistant import SplAssistantSuggestResponse
from models.handoff import SplunkAlertIngest
from models.observability import ObservabilityRunRequest
from services.alert.alert_mcp_enrichment import classify_with_optional_mcp
from services.alert.alert_pipeline import enrich_alert_from_splunk
from services.observability_analysis import run_observability_analysis
from services.soc_analysis import append_analysis_log, run_analysis
from services.triage.triage_priority import merge_triage_into_analysis_output
from services.splunk_integration.splunk_ai_assistant import suggest_spl_for_alert
from services.inventory.inventory_loader import IncompleteOfflineInventoryError, load_inventory_tables
from services.soc_analysis.analysis_audit import (
    build_analysis_input,
    build_analysis_output,
    build_raw_alert,
    format_row_sid,
    resolve_storage_context,
    splunk_job_sid,
)
from services.alert.ingest_row_shape import detect_splunk_result_row_shape, log_splunk_result_row_shape
from services.soc_analysis.soc_analysis_batch import merge_normalized_for_row
from services.splunk_json_store import persist_agentic_ops_route_to_splunk

logger = logging.getLogger(__name__)


def build_next_actions(classification: AlertClassificationResult) -> list[str]:
    actions = ["Validate severity and entity context against inventory (users, assets, relationships)."]
    if classification.recommended_pipeline == "security":
        actions.append("Review Judge verdict and execute the recommended SOC containment step.")
    elif classification.recommended_pipeline == "observability":
        actions.append("Review Ops Judge verdict and start service remediation runbook.")
    if classification.needs_human_routing or classification.recommended_pipeline == "manual_review":
        actions.append("Manual routing required: assign to SOC or ITOps lead.")
    actions.append("Run suggested SPL to collect root-cause evidence.")
    return actions


async def run_agent_triage(settings: Settings, body: AgentTriageRequest) -> AgentTriageResponse:
    t0 = time.perf_counter()
    try:
        users, assets, relationships = await load_inventory_tables(
            settings, body.users, body.assets, body.relationships
        )
    except IncompleteOfflineInventoryError:
        raise
    except ValueError:
        raise
    except Exception as e:
        raise RuntimeError(
            "Inventory load failed (check app name, transforms, and permissions): {0}".format(e)
        ) from e

    rows = list(body.splunk_results or [])
    base_sid = splunk_job_sid(body.sid) or (body.sid or "")
    if not rows and base_sid:
        enriched = await enrich_alert_from_splunk(
            SplunkAlertIngest(sid=base_sid, search_name=body.search_name, normalized=body.normalized),
            settings,
        )
        rows = list(enriched.get("splunk_results") or [])

    storage_sid, row_index, job_row_count = resolve_storage_context(
        sid=body.sid,
        splunk_results=rows,
        row_index=body.row_index,
        job_row_count=body.job_row_count,
    )
    row_slice = list(rows)
    if len(rows) > 1:
        if row_index >= len(rows):
            row_index = len(rows) - 1
        row_slice = [rows[row_index]]
    raw_alert = build_raw_alert(
        sid=storage_sid,
        search_name=body.search_name,
        normalized=body.normalized,
        splunk_results=row_slice,
        row_index=row_index,
        job_row_count=job_row_count,
    )
    analysis_input = build_analysis_input(
        search_name=body.search_name,
        normalized=body.normalized,
        splunk_results=row_slice,
        row_index=row_index,
    )

    classification, mcp_context, mcp_used = await classify_with_optional_mcp(
        settings,
        normalized=body.normalized,
        search_name=body.search_name,
        splunk_results=row_slice,
        sid=storage_sid,
    )
    security_result = None
    observability_result = None
    security_triage = None
    observability_triage = None
    analysis_output = None

    if classification.recommended_pipeline == "security":
        sec_body = AnalysisRunRequest(
            normalized=body.normalized,
            search_name=body.search_name,
            sid=storage_sid,
            row_index=row_index,
            splunk_results=row_slice,
        )
        security_result = await run_analysis(
            settings,
            sec_body,
            users=users,
            assets=assets,
            relationships=relationships,
            analysis_row_index=row_index,
            classification=classification,
        )
        append_analysis_log(settings, security_result)
        analysis_output = build_analysis_output(security_result)
        security_triage = security_result.triage

    elif classification.recommended_pipeline == "observability":
        obs_body = ObservabilityRunRequest(
            normalized=body.normalized,
            search_name=body.search_name,
            sid=storage_sid,
            splunk_results=row_slice,
        )
        observability_result = await run_observability_analysis(
            settings,
            obs_body,
            users=users,
            assets=assets,
            relationships=relationships,
            classification=classification,
        )
        observability_triage = observability_result.triage
        analysis_output = merge_triage_into_analysis_output(
            {
                "verdict": observability_result.ops_judge.verdict,
                "priority": observability_result.ops_judge.priority,
                "recommended_next_step": observability_result.ops_judge.recommended_next_step,
                "confidence": observability_result.ops_judge.confidence,
                "rationale": observability_result.ops_judge.rationale,
                "summary": observability_result.summary,
            },
            observability_triage,
        )

    enrichment_for_spl = None
    if security_result is not None and security_result.enrichment is not None:
        enrichment_for_spl = security_result.enrichment.model_dump(mode="json")

    rc, src = await suggest_spl_for_alert(
        settings,
        normalized=body.normalized,
        search_name=body.search_name,
        sid=storage_sid,
        splunk_results=row_slice,
        objective=body.operator_goal,
        enrichment=enrichment_for_spl,
    )
    suggested_spl = SplAssistantSuggestResponse(source=src, root_cause_spl=rc)

    await persist_agentic_ops_route_to_splunk(
        settings,
        sid=storage_sid,
        search_name=body.search_name,
        classification=classification,
        security_result=security_result,
        observability_result=observability_result,
        mcp_context=mcp_context,
        mcp_used=mcp_used,
        row_index=row_index,
        raw_alert=raw_alert,
        analysis_input=analysis_input,
        analysis_output=analysis_output,
    )

    next_actions = build_next_actions(classification)
    summary = "Agent routed alert to {0} pipeline with confidence {1:.2f}.".format(
        classification.recommended_pipeline, classification.confidence
    )
    logger.info(
        "agent_triage done sid=%s pipeline=%s source=%s duration_ms=%.1f",
        storage_sid,
        classification.recommended_pipeline,
        classification.classification_source,
        (time.perf_counter() - t0) * 1000.0,
    )
    return AgentTriageResponse(
        track=classification.track,
        classification=classification,
        agent_summary=summary,
        next_actions=next_actions,
        security_result=security_result,
        observability_result=observability_result,
        security_triage=security_triage,
        observability_triage=observability_triage,
        suggested_spl=suggested_spl,
        mcp_used=mcp_used,
        mcp_context=mcp_context,
    )


async def run_agent_triage_all_rows(
    settings: Settings,
    body: AgentTriageRequest,
    *,
    max_rows: Optional[int] = None,
    stop_on_first_error: bool = False,
) -> List[AgentTriageResponse]:
    """
    Run agent triage once per Splunk result row, **sequentially** (row 1, then 2, …).

    When the job has multiple rows, each analysis is stored under ``{sid}-{row}``
    (1-based row number). Single-row jobs keep the original sid.
    """
    rows = list(body.splunk_results or [])
    base_sid = splunk_job_sid(body.sid) or (body.sid or "")
    if not rows and base_sid:
        enriched = await enrich_alert_from_splunk(
            SplunkAlertIngest(sid=base_sid, search_name=body.search_name, normalized=body.normalized),
            settings,
        )
        rows = list(enriched.get("splunk_results") or [])

    cap_default = int(getattr(settings, "tsoc_ingest_auto_analyze_max_rows", 50) or 50)
    effective_max = max_rows if max_rows is not None else cap_default
    row_shape = detect_splunk_result_row_shape(
        sid=base_sid or body.sid,
        total_rows=len(rows),
        max_rows=effective_max,
    )
    log_splunk_result_row_shape(
        stage="triage_dispatch",
        search_name=body.search_name,
        shape=row_shape,
        log=logger,
    )

    if len(rows) <= 1:
        single = body.model_copy(update={"sid": base_sid or body.sid, "splunk_results": rows})
        return [await run_agent_triage(settings, single)]

    cap = max_rows if max_rows is not None else int(
        getattr(settings, "tsoc_ingest_auto_analyze_max_rows", 50) or 50
    )
    cap = max(1, min(500, cap))
    slice_rows = rows[: min(cap, len(rows))]
    base_norm = body.normalized or {}
    outcomes: List[AgentTriageResponse] = []

    ok_count = 0
    fail_count = 0
    for i, row in enumerate(slice_rows):
        merged = merge_normalized_for_row(base_norm, row)
        storage_sid = format_row_sid(base_sid, i, len(rows))
        row_body = body.model_copy(
            update={
                "sid": storage_sid,
                "normalized": merged,
                "splunk_results": [row],
                "row_index": i,
                "job_row_count": len(rows),
            }
        )
        row_num = i + 1
        logger.info(
            "agent_triage_all_rows start base_sid=%s row=%d/%d storage_sid=%s",
            base_sid,
            row_num,
            len(rows),
            storage_sid,
        )
        try:
            outcomes.append(await run_agent_triage(settings, row_body))
            ok_count += 1
            logger.info(
                "agent_triage_all_rows done row=%d/%d storage_sid=%s",
                row_num,
                len(rows),
                storage_sid,
            )
        except Exception as e:
            fail_count += 1
            logger.warning(
                "agent_triage_all_rows failed row=%d/%d storage_sid=%s err=%s",
                row_num,
                len(rows),
                storage_sid,
                e,
                exc_info=True,
            )
            if stop_on_first_error:
                raise
            continue

    logger.info(
        "agent_triage_all_rows finished base_sid=%s total_rows=%d analyzed=%d ok=%d fail=%d",
        base_sid,
        len(rows),
        len(outcomes),
        ok_count,
        fail_count,
    )
    return outcomes
