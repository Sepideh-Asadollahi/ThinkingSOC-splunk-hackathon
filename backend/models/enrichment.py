"""Alert enrichment from inventory + user–asset relationships."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class EnrichmentResult(BaseModel):
    resolved_asset_id: Optional[str] = None
    resolved_user_id: Optional[str] = None
    confidence: Literal["high", "medium", "low"]
    notes: str
    matched_relationship_ids: List[str] = Field(default_factory=list)


class EnrichRequest(BaseModel):
    """Match a normalized alert against inventory (optional offline payload)."""

    normalized: Dict[str, Any] = Field(default_factory=dict)
    users: Optional[List[Dict[str, Any]]] = None
    assets: Optional[List[Dict[str, Any]]] = None
    relationships: Optional[List[Dict[str, Any]]] = None
