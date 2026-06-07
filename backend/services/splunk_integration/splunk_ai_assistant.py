"""Generate analyst-ready SPL via REST /predict, LiteLLM, or rule-based ``search`` fallback."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from config import Settings
from models.analysis import RootCauseSpl
from services.soc_analysis.soc_analysis_canonical import build_canonical_static_context
from services.soc_analysis.soc_analysis_root_cause_spl import build_rule_based_root_cause_spl, validate_root_cause_spl
from services.investigation.spl_mcp_review import (
    refine_root_cause_spl_until_valid,
    spl_validation_is_error,
)
from services.investigation.spl_predict_pipeline import (
    SPL_ALL_TIME_WINDOW,
    build_predict_prompt,
    execute_spl_via_mcp,
    generate_spl_via_predict,
)

logger = logging.getLogger(__name__)


async def _validate_and_refine_spl_on_error(
    settings: Settings,
    rc: RootCauseSpl,
    *,
    normalized: Dict[str, Any],
    search_name: Optional[str],
    sid: Optional[str],
    splunk_results: List[Dict[str, Any]],
    objective: Optional[str],
    enrichment: Optional[Dict[str, Any]] = None,
) -> RootCauseSpl:
    rc.validation = await validate_root_cause_spl(settings, rc)
    if spl_validation_is_error(rc.validation):
        rc, _ = await refine_root_cause_spl_until_valid(
            settings,
            rc,
            normalized=normalized,
            search_name=search_name,
            sid=sid,
            splunk_results=splunk_results,
            objective=objective,
            enrichment=enrichment,
        )
    return rc


def _default_enrichment() -> Dict[str, Any]:
    return {
        "resolved_asset_id": None,
        "resolved_user_id": None,
        "matched_relationship_ids": [],
        "confidence": "low",
        "notes": "No explicit identity resolution provided for assistant suggestion.",
    }


async def _generate_spl_via_llm(
    settings: Settings,
    *,
    normalized: Dict[str, Any],
    search_name: Optional[str],
    sid: Optional[str],
    splunk_results: List[Dict[str, Any]],
    objective: Optional[str],
    enrichment: Dict[str, Any],
) -> Optional[RootCauseSpl]:
    from services.investigation.investigation_questions_spl import generate_investigation_spl_via_llm

    canonical = build_canonical_static_context(
        normalized=normalized,
        search_name=search_name,
        sid=sid,
        splunk_results_preview=(splunk_results or [])[:5],
        enrichment=enrichment,
        risk_context="",
        inventory_user=None,
        inventory_asset=None,
    )
    return await generate_investigation_spl_via_llm(
        settings,
        question=objective or "Generate root-cause SPL for this alert.",
        canonical_prefix=canonical,
        defender_output={},
        hunter_output={},
        judge_output={},
        normalized=normalized,
        search_name=search_name or "",
    )


async def suggest_spl_for_alert(
    settings: Settings,
    *,
    normalized: Dict[str, Any],
    search_name: Optional[str],
    sid: Optional[str],
    splunk_results: List[Dict[str, Any]],
    objective: Optional[str],
    enrichment: Optional[Dict[str, Any]] = None,
) -> Tuple[RootCauseSpl, str]:
    """
    SPL pipeline: REST /predict (UI path) → MCP execute (All Time) → LiteLLM → rule-based.
    """
    identity = enrichment or _default_enrichment()

    if getattr(settings, "tsoc_spl_use_rest_predict", True):
        prompt = build_predict_prompt(
            objective=objective,
            search_name=search_name,
            normalized=normalized,
            splunk_results=splunk_results,
        )
        predict_rc = await generate_spl_via_predict(settings, prompt=prompt)
        if predict_rc is not None and predict_rc.spl:
            predict_rc = await _validate_and_refine_spl_on_error(
                settings,
                predict_rc,
                normalized=normalized,
                search_name=search_name,
                sid=sid,
                splunk_results=splunk_results,
                objective=objective,
                enrichment=identity,
            )
            source = "rest_predict"
            if getattr(settings, "tsoc_execute_investigation_spl", True):
                predict_rc.spl_results = await execute_spl_via_mcp(settings, predict_rc.spl)
                predict_rc.time_window = SPL_ALL_TIME_WINDOW
                if predict_rc.spl_results and predict_rc.spl_results.error:
                    source = "rest_predict_execute_error"
                elif predict_rc.spl_results and (predict_rc.spl_results.row_count or 0) > 0:
                    source = "rest_predict_execute"
                else:
                    source = "rest_predict_execute_empty"
            return predict_rc, source

    if getattr(settings, "tsoc_spl_use_rest_predict", True):
        logger.info(
            "investigation_spl next_step=litellm_spl reason=saia_predict_unavailable_or_empty "
            "not_an_analysis_failure=true"
        )

    llm_rc = await _generate_spl_via_llm(
        settings,
        normalized=normalized,
        search_name=search_name,
        sid=sid,
        splunk_results=splunk_results,
        objective=objective,
        enrichment=identity,
    )
    if llm_rc is not None and llm_rc.spl:
        llm_rc = await _validate_and_refine_spl_on_error(
            settings,
            llm_rc,
            normalized=normalized,
            search_name=search_name,
            sid=sid,
            splunk_results=splunk_results,
            objective=objective,
            enrichment=identity,
        )
        if getattr(settings, "tsoc_execute_investigation_spl", True):
            llm_rc.spl_results = await execute_spl_via_mcp(settings, llm_rc.spl)
            llm_rc.time_window = SPL_ALL_TIME_WINDOW
        return llm_rc, "llm"

    rc = build_rule_based_root_cause_spl(normalized)
    rc = await _validate_and_refine_spl_on_error(
        settings,
        rc,
        normalized=normalized,
        search_name=search_name,
        sid=sid,
        splunk_results=splunk_results,
        objective=objective,
        enrichment=identity,
    )
    if getattr(settings, "tsoc_execute_investigation_spl", True):
        rc.spl_results = await execute_spl_via_mcp(settings, rc.spl)
        rc.time_window = SPL_ALL_TIME_WINDOW
    return rc, "rule_based"
