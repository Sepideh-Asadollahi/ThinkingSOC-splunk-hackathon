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
from services.soc_analysis.soc_analysis_risk import find_asset_row, find_user_row
from services.triage.triage_priority import (
    compute_triage_from_observability,
    compute_triage_from_soc,
    merge_triage_into_analysis_output,
)
from services.splunk_integration.splunk_ai_assistant import suggest_spl_for_alert
from services.inventory.inventory_loader import IncompleteOfflineInventoryError, load_inventory_tables
from services.soc_analysis.analysis_audit import (
    build_analysis_input,
    build_analysis_output,
    build_raw_alert,
    resolve_row_index,
)
from services.splunk_json_store import (
    persist_agentic_ops_route_to_splunk,
    persist_observability_analysis_to_splunk,
    persist_soc_analysis_to_splunk,
)

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
    if not rows and body.sid:
        enriched = await enrich_alert_from_splunk(
            SplunkAlertIngest(sid=body.sid, search_name=body.search_name, normalized=body.normalized),
            settings,
        )
        rows = list(enriched.get("splunk_results") or [])

    row_index = resolve_row_index(body.row_index, rows)
    if rows and row_index >= len(rows):
        row_index = len(rows) - 1
    row_slice = [rows[row_index]] if rows else []
    raw_alert = build_raw_alert(
        sid=body.sid,
        search_name=body.search_name,
        normalized=body.normalized,
        splunk_results=rows,
        row_index=row_index,
    )
    analysis_input = build_analysis_input(
        search_name=body.search_name,
        normalized=body.normalized,
        splunk_results=rows,
        row_index=row_index,
    )

    classification, mcp_context, mcp_used = await classify_with_optional_mcp(
        settings,
        normalized=body.normalized,
        search_name=body.search_name,
        splunk_results=row_slice or rows,
        sid=body.sid,
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
            sid=body.sid,
            row_index=row_index,
            splunk_results=row_slice or rows,
        )
        security_result = await run_analysis(
            settings,
            sec_body,
            users=users,
            assets=assets,
            relationships=relationships,
            analysis_row_index=row_index,
        )
        id_res = security_result.enrichment
        security_triage = compute_triage_from_soc(
            security_result,
            classification=classification,
            user_row=find_user_row(users, id_res.resolved_user_id),
            asset_row=find_asset_row(assets, id_res.resolved_asset_id),
        )
        security_result = security_result.model_copy(update={"triage": security_triage})
        append_analysis_log(settings, security_result)
        analysis_output = build_analysis_output(security_result)
        await persist_soc_analysis_to_splunk(
            settings,
            sec_body,
            security_result,
            row_index=row_index,
            raw_alert=raw_alert,
            analysis_input=analysis_input,
            analysis_output=analysis_output,
        )

    elif classification.recommended_pipeline == "observability":
        obs_body = ObservabilityRunRequest(
            normalized=body.normalized,
            search_name=body.search_name,
            sid=body.sid,
            splunk_results=row_slice or rows,
        )
        observability_result = await run_observability_analysis(
            settings, obs_body, users=users, assets=assets, relationships=relationships
        )
        observability_triage = compute_triage_from_observability(
            observability_result,
            classification=classification,
        )
        observability_result = observability_result.model_copy(update={"triage": observability_triage})
        await persist_observability_analysis_to_splunk(
            settings,
            obs_body,
            observability_result,
            row_index=row_index,
            raw_alert=raw_alert,
            analysis_input=analysis_input,
            analysis_output=merge_triage_into_analysis_output(
                {
                    "verdict": observability_result.ops_judge.verdict,
                    "priority": observability_result.ops_judge.priority,
                    "recommended_next_step": observability_result.ops_judge.recommended_next_step,
                    "confidence": observability_result.ops_judge.confidence,
                    "rationale": observability_result.ops_judge.rationale,
                    "summary": observability_result.summary,
                },
                observability_triage,
            ),
        )

    enrichment_for_spl = None
    if security_result is not None and security_result.enrichment is not None:
        enrichment_for_spl = security_result.enrichment.model_dump(mode="json")

    rc, src = await suggest_spl_for_alert(
        settings,
        normalized=body.normalized,
        search_name=body.search_name,
        sid=body.sid,
        splunk_results=rows,
        objective=body.operator_goal,
        enrichment=enrichment_for_spl,
    )
    suggested_spl = SplAssistantSuggestResponse(source=src, root_cause_spl=rc)

    await persist_agentic_ops_route_to_splunk(
        settings,
        sid=body.sid,
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
        body.sid,
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
