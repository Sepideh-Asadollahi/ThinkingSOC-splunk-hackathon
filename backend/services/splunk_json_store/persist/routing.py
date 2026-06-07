"""Persist agentic ops routing results."""

from __future__ import annotations

from typing import Any, Dict, Optional

from config import Settings
from models.agentic_ops import AlertClassificationResult
from models.analysis import SocAnalysisResult
from models.mcp import McpAlertContext
from models.observability import ObservabilityAnalysisResult

from .. import pg
from ._common import stored_at_iso


async def persist_agentic_ops_route_to_splunk(
    settings: Settings,
    *,
    sid: Optional[str],
    search_name: Optional[str],
    classification: AlertClassificationResult,
    security_result: Optional[SocAnalysisResult],
    observability_result: Optional[ObservabilityAnalysisResult],
    mcp_context: Optional[McpAlertContext] = None,
    mcp_used: bool = False,
    row_index: int = 0,
    raw_alert: Optional[Dict[str, Any]] = None,
    analysis_input: Optional[Dict[str, Any]] = None,
    analysis_output: Optional[Dict[str, Any]] = None,
) -> None:
    if not pg.splunk_store_configured(settings):
        return
    payload: Dict[str, Any] = {
        "tsoc_record_type": "agentic_ops_analysis",
        "stored_at": stored_at_iso(),
        "sid": sid,
        "search_name": search_name,
        "row_index": row_index,
        "raw_alert": raw_alert,
        "analysis_input": analysis_input,
        "analysis_output": analysis_output,
        "classification": classification.model_dump(mode="json"),
        "security_result": security_result.model_dump(mode="json") if security_result is not None else None,
        "observability_result": observability_result.model_dump(mode="json")
        if observability_result is not None
        else None,
        "mcp_used": mcp_used,
        "mcp_context": mcp_context.model_dump(mode="json") if mcp_context is not None else None,
    }
    await pg.submit_hec_event(settings, payload)
