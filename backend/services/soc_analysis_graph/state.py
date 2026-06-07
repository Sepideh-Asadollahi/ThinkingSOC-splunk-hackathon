"""LangGraph state shape for the SOC analysis pipeline."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict


class SocAnalysisGraphState(TypedDict, total=False):
    """State carried through the graph (serializable dict)."""

    normalized: Dict[str, Any]
    search_name: Optional[str]
    sid: Optional[str]
    row_index: int
    splunk_results_preview: List[Dict[str, Any]]
    enrichment: Dict[str, Any]
    inventory_user: Optional[Dict[str, Any]]
    inventory_asset: Optional[Dict[str, Any]]
    risk_context: str
    threat_intel: Dict[str, Any]
    similar_alert_context: Dict[str, Any]
    canonical_prefix: str
    defender_output: Dict[str, Any]
    hunter_output: Dict[str, Any]
    judge_output: Dict[str, Any]
    hunter_mcp_context: Dict[str, Any]
    judge_mcp_context: Dict[str, Any]
    framework_mapping_output: Dict[str, Any]
    investigation_questions_output: Dict[str, Any]
    root_cause_spl_output: Dict[str, Any]
