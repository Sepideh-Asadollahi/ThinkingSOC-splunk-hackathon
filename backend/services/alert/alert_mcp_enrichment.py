"""Shared MCP enrichment before alert classification."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from config import Settings, mcp_configured
from models.agentic_ops import AlertClassificationResult
from models.mcp import McpAlertContext
from services.alert.alert_classifier_llm import classify_alert_hybrid, ensure_exclusive_classification
from splunk.mcp.context_builder import build_mcp_alert_context


async def classify_with_optional_mcp(
    settings: Settings,
    *,
    normalized: Dict[str, Any],
    search_name: Optional[str],
    splunk_results: List[Dict[str, Any]],
    sid: Optional[str] = None,
) -> Tuple[AlertClassificationResult, Optional[McpAlertContext], bool]:
    """
    Classify alert via LLM using full alert payload and optional Splunk MCP metadata.

    Returns (classification, mcp_context, mcp_used).
    """
    mcp_context: Optional[McpAlertContext] = None
    mcp_used = False

    if mcp_configured(settings):
        mcp_context = await build_mcp_alert_context(
            settings,
            normalized=normalized,
            search_name=search_name,
            splunk_results=splunk_results,
        )
        if mcp_context and mcp_context.tools_called:
            mcp_used = True

    classification = ensure_exclusive_classification(
        await classify_alert_hybrid(
            settings,
            normalized,
            search_name,
            splunk_results,
            sid=sid,
            mcp_context=mcp_context,
        )
    )
    if mcp_used and mcp_context:
        classification.reason = "{0} Splunk MCP enriched ({1} tool calls).".format(
            classification.reason,
            len(mcp_context.tools_called),
        )
    return classification, mcp_context, mcp_used
