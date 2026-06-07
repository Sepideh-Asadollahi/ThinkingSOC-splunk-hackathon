"""Pydantic models for SOC vector RAG subsystem."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class RagAlertDocument(BaseModel):
    doc_type: str = "splunk_alert"
    doc_id: str
    sid: Optional[str] = None
    search_name: Optional[str] = None
    row_index: int = 0
    essential: Dict[str, Any] = Field(default_factory=dict)
    summary_line: str = ""
    chunk_text: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SimilarAlertItem(BaseModel):
    sid: Optional[str] = None
    search_name: Optional[str] = None
    _time: Optional[str] = None
    essential: Dict[str, Any] = Field(default_factory=dict)
    prior_verdict: Optional[str] = None
    similarity_score: float = 0.0
    doc_type: str = "splunk_alert"


class SimilarAlertContext(BaseModel):
    similar_alerts: List[SimilarAlertItem] = Field(default_factory=list)
    retrieval_meta: Dict[str, Any] = Field(default_factory=dict)


class SocChatCitation(BaseModel):
    doc_id: str
    sid: Optional[str] = None
    search_name: Optional[str] = None
    summary_line: str = ""
    doc_type: str = "splunk_alert"
    similarity_score: Optional[float] = None


class SocChatMessage(BaseModel):
    role: str
    content: str


class SocChatFilters(BaseModel):
    severity: Optional[List[str]] = None
    lookback_days: Optional[int] = Field(default=None, ge=1, le=365)
    search_name_prefix: Optional[str] = None
    doc_types: Optional[List[str]] = None


class SocChatSqlMeta(BaseModel):
    query_mode: Literal["sql", "rag", "analysis_queue"] = "sql"
    sql: Optional[str] = None
    row_count: Optional[int] = None
    tables_used: Optional[List[str]] = None


class SocChatRequest(BaseModel):
    messages: List[SocChatMessage] = Field(..., min_length=1)
    filters: Optional[SocChatFilters] = None
    conversation_id: Optional[str] = None


class SocChatConversationSummary(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int = 0


class SocChatStoredMessage(BaseModel):
    role: str
    content: str
    message_id: Optional[int] = None
    seq: Optional[int] = None
    sql_meta: Optional[SocChatSqlMeta] = None


class SocChatConversationDetail(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    messages: List[SocChatStoredMessage] = Field(default_factory=list)


class SocChatCreateConversationRequest(BaseModel):
    title: Optional[str] = None


class SocChatResponse(BaseModel):
    answer: str
    citations: List[SocChatCitation] = Field(default_factory=list)
    splunk_mcp_used: bool = False
    retrieval_backend: str = "postgres"
    retrieval_meta: Dict[str, Any] = Field(default_factory=dict)
    sql_meta: Optional[SocChatSqlMeta] = None
    conversation_id: Optional[str] = None
