"""Admin organizational context — GAP question suggestion (hackathon, no DB)."""

from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class AdminOrgGapSuggestRequest(BaseModel):
    """Alert + optional SOC analysis excerpts for gap detection."""

    normalized: Dict[str, Any] = Field(default_factory=dict)
    sid: Optional[str] = None
    search_name: Optional[str] = None
    enrichment: Optional[Dict[str, Any]] = None
    risk_context: Optional[str] = None
    defender_text: Optional[str] = None
    hunter_text: Optional[str] = None
    judge_verdict: Optional[str] = None
    judge_rationale: Optional[str] = None
    inventory_user: Optional[Dict[str, Any]] = None
    inventory_asset: Optional[Dict[str, Any]] = None


class AdminOrgGapSuggestResponse(BaseModel):
    """LLM (or rule fallback) output: should we ask the admin, and what to ask."""

    should_suggest_question: bool
    gap_summary: str = ""
    question_for_admin: str = ""
    notes: Optional[str] = None
