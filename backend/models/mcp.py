"""API models for Splunk MCP integration."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class McpToolInfo(BaseModel):
    name: str
    description: Optional[str] = None


class McpQueryEvidence(BaseModel):
    """One MCP ``splunk_run_query`` result attached to Hunter/Judge reasoning."""

    query: str
    row_count: int = 0
    summary: str = ""
    error: Optional[str] = None


class McpSaiaAnswer(BaseModel):
    """Answer from MCP ``saia_ask_splunk_question`` for Judge context."""

    question: str
    answer: str


class McpHunterEvidence(BaseModel):
    """Splunk MCP evidence gathered before the Hunter LLM stage."""

    tools_called: List[str] = Field(default_factory=list)
    hunt_queries: List[McpQueryEvidence] = Field(default_factory=list)
    metadata_sourcetypes: List[str] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)


class McpJudgeEvidence(BaseModel):
    """Splunk MCP evidence gathered before the Judge LLM stage."""

    tools_called: List[str] = Field(default_factory=list)
    saia_answers: List[McpSaiaAnswer] = Field(default_factory=list)
    verification_queries: List[McpQueryEvidence] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)


class McpAlertContext(BaseModel):
    """Splunk MCP enrichment attached to alert triage/routing."""

    tools_called: List[str] = Field(default_factory=list)
    metadata_hosts: List[str] = Field(default_factory=list)
    metadata_sources: List[str] = Field(default_factory=list)
    metadata_sourcetypes: List[str] = Field(default_factory=list)
    indexes: List[str] = Field(default_factory=list)
    instance_info: Dict[str, Any] = Field(default_factory=dict)
    correlation_query: Optional[str] = None
    correlation_summary: Optional[str] = None
    notes: List[str] = Field(default_factory=list)
    raw_snippets: Dict[str, Any] = Field(default_factory=dict)


class McpStatusResponse(BaseModel):
    configured: bool
    connected: bool = False
    url: Optional[str] = None
    server_info: Dict[str, Any] = Field(default_factory=dict)
    tools: List[str] = Field(default_factory=list)
    saia_available: bool = False
    message: Optional[str] = None


class McpToolCallRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)


class McpToolCallResponse(BaseModel):
    tool_name: str
    result: Any = None


class McpSplGenerateRequest(BaseModel):
    """Natural-language SPL generation via Splunk MCP (saia_generate_spl)."""

    query: str = Field(description="Natural language description of the desired SPL/search.")
    index: Optional[str] = None
    context: Optional[str] = Field(
        default=None,
        description="Optional alert/search context for the Assistant.",
    )


class McpSplGenerateResponse(BaseModel):
    source: Literal["splunk_mcp_saia", "unavailable"]
    spl: Optional[str] = None
    explanation: Optional[str] = None
    raw: Any = None
