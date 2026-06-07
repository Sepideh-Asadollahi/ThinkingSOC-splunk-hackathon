"""Splunk AI Assistant style request/response contracts."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from models.analysis import RootCauseSpl, SplSearchResult
from models.enrichment import EnrichmentResult


class SplAssistantSuggestRequest(BaseModel):
    """Generate one analyst-ready SPL for next investigation step."""

    normalized: Dict[str, Any] = Field(default_factory=dict)
    search_name: Optional[str] = None
    sid: Optional[str] = None
    splunk_results: List[Dict[str, Any]] = Field(default_factory=list)
    objective: Optional[str] = Field(
        default=None,
        description="Optional analyst intent, e.g. 'find first lateral movement evidence'.",
    )
    enrichment: Optional[EnrichmentResult] = None


class SplAssistantSuggestResponse(BaseModel):
    source: Literal[
        "llm",
        "rule_based",
        "rest_predict",
        "rest_predict_execute",
        "rest_predict_execute_empty",
        "rest_predict_execute_error",
    ]
    root_cause_spl: RootCauseSpl
    spl_results: Optional[SplSearchResult] = Field(
        default=None,
        description="MCP execute results (mirror of root_cause_spl.spl_results when present).",
    )

