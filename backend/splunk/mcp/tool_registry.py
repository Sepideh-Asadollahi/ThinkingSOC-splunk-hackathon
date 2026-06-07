"""Map logical MCP operations to Splunk tool names (with doc/version aliases)."""

from __future__ import annotations

from enum import Enum
from typing import Iterable, List, Optional


class McpLogicalTool(str, Enum):
    SAIA_GENERATE_SPL = "saia_generate_spl"
    SAIA_OPTIMIZE_SPL = "saia_optimize_spl"
    SAIA_EXPLAIN_SPL = "saia_explain_spl"
    SAIA_ASK_SPLUNK_QUESTION = "saia_ask_splunk_question"
    SPLUNK_GET_INFO = "splunk_get_info"
    SPLUNK_GET_METADATA = "splunk_get_metadata"
    SPLUNK_RUN_QUERY = "splunk_run_query"
    SPLUNK_GET_INDEXES = "splunk_get_indexes"


# Primary name first; aliases from older READMEs / previews.
_TOOL_ALIASES: dict[McpLogicalTool, tuple[str, ...]] = {
    McpLogicalTool.SAIA_GENERATE_SPL: ("saia_generate_spl", "generate_spl"),
    McpLogicalTool.SAIA_OPTIMIZE_SPL: ("saia_optimize_spl", "optimize_spl"),
    McpLogicalTool.SAIA_EXPLAIN_SPL: ("saia_explain_spl", "explain_spl"),
    McpLogicalTool.SAIA_ASK_SPLUNK_QUESTION: ("saia_ask_splunk_question", "ask_splunk_question"),
    McpLogicalTool.SPLUNK_GET_INFO: ("splunk_get_info", "get_splunk_info"),
    McpLogicalTool.SPLUNK_GET_METADATA: ("splunk_get_metadata", "get_metadata"),
    McpLogicalTool.SPLUNK_RUN_QUERY: ("splunk_run_query", "run_splunk_query"),
    McpLogicalTool.SPLUNK_GET_INDEXES: ("splunk_get_indexes", "get_indexes"),
}


def resolve_tool_name(available_tools: Iterable[str], logical: McpLogicalTool) -> Optional[str]:
    """Return the first alias present in ``available_tools``, or None."""
    avail = {t.strip() for t in available_tools if t}
    for candidate in _TOOL_ALIASES.get(logical, (logical.value,)):
        if candidate in avail:
            return candidate
    return None


def saia_tool_names(available_tools: Iterable[str]) -> List[str]:
    """All ``saia_*`` tools exposed by the server."""
    return sorted(t for t in available_tools if t.startswith("saia_"))
