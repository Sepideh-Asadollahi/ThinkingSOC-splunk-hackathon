"""Build alert context from Splunk MCP tools (metadata, optional correlation)."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from config import Settings, mcp_configured
from models.mcp import McpAlertContext

from .client import SplunkMcpClient
from .errors import McpConnectionError, McpNotConfiguredError, McpToolError
from .tool_registry import McpLogicalTool, resolve_tool_name

logger = logging.getLogger(__name__)


def _extract_string_list(raw: Any, keys: tuple[str, ...]) -> List[str]:
    out: List[str] = []
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return [raw] if raw else []
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, str):
                out.append(item)
            elif isinstance(item, dict):
                for k in keys:
                    if item.get(k):
                        out.append(str(item[k]))
                        break
    elif isinstance(raw, dict):
        for k in keys:
            val = raw.get(k)
            if isinstance(val, list):
                out.extend(str(x) for x in val)
            elif val:
                out.append(str(val))
    return sorted(set(x for x in out if x))


async def build_mcp_alert_context(
    settings: Settings,
    *,
    normalized: Dict[str, Any],
    search_name: Optional[str],
    splunk_results: List[Dict[str, Any]],
) -> Optional[McpAlertContext]:
    """
    Enrich alert with Splunk MCP metadata (and optional correlation query).

    Returns None when MCP is not configured or all tool calls fail.
    """
    if not mcp_configured(settings):
        return None

    ctx = McpAlertContext()
    try:
        client = SplunkMcpClient(settings)
        await client.ensure_ready()
    except (McpConnectionError, McpNotConfiguredError, McpToolError) as e:
        logger.warning("mcp context: client init failed: %s", e)
        ctx.notes.append("MCP client unavailable: {0}".format(e))
        return ctx

    # Instance info (status / demo)
    if resolve_tool_name(client.tool_names, McpLogicalTool.SPLUNK_GET_INFO):
        try:
            info = await client.call_tool(McpLogicalTool.SPLUNK_GET_INFO, {})
            if isinstance(info, dict):
                ctx.instance_info = info
            else:
                ctx.instance_info = {"summary": str(info)[:500]}
            ctx.tools_called.append("splunk_get_info")
        except McpToolError as e:
            ctx.notes.append("get_info failed: {0}".format(e))

    # Indexes hint
    if resolve_tool_name(client.tool_names, McpLogicalTool.SPLUNK_GET_INDEXES):
        try:
            idx_raw = await client.call_tool(McpLogicalTool.SPLUNK_GET_INDEXES, {})
            ctx.indexes = _extract_string_list(idx_raw, ("name", "title", "index"))
            ctx.tools_called.append("splunk_get_indexes")
            ctx.raw_snippets["indexes"] = idx_raw if isinstance(idx_raw, (dict, list)) else str(idx_raw)[:300]
        except McpToolError as e:
            ctx.notes.append("get_indexes failed: {0}".format(e))

    # Metadata for host/source discovery
    index = "*"
    if isinstance(normalized.get("index"), str) and normalized["index"].strip():
        index = normalized["index"].strip()

    meta_args: Dict[str, Any] = {
        "index": index,
        "type": "hosts",
        "earliest_time": "0",
        "latest_time": "now",
    }

    if resolve_tool_name(client.tool_names, McpLogicalTool.SPLUNK_GET_METADATA):
        try:
            meta_hosts = await client.call_tool(McpLogicalTool.SPLUNK_GET_METADATA, meta_args)
            ctx.metadata_hosts = _extract_string_list(meta_hosts, ("host", "name", "value"))
            ctx.tools_called.append("splunk_get_metadata:hosts")
            ctx.raw_snippets["metadata_hosts"] = (
                meta_hosts if isinstance(meta_hosts, (dict, list)) else str(meta_hosts)[:400]
            )

            meta_args["type"] = "sources"
            meta_sources = await client.call_tool(McpLogicalTool.SPLUNK_GET_METADATA, meta_args)
            ctx.metadata_sources = _extract_string_list(meta_sources, ("source", "name", "value"))
            ctx.tools_called.append("splunk_get_metadata:sources")

            meta_args["type"] = "sourcetypes"
            meta_st = await client.call_tool(McpLogicalTool.SPLUNK_GET_METADATA, meta_args)
            ctx.metadata_sourcetypes = _extract_string_list(meta_st, ("sourcetype", "name", "value"))
            ctx.tools_called.append("splunk_get_metadata:sourcetypes")
        except McpToolError as e:
            ctx.notes.append("get_metadata failed: {0}".format(e))

    if settings.tsoc_mcp_correlation_enabled and resolve_tool_name(
        client.tool_names, McpLogicalTool.SPLUNK_RUN_QUERY
    ):
        spl = _safe_correlation_spl(normalized, search_name)
        if spl:
            try:
                ctx.correlation_query = spl
                q_result = await client.call_tool(
                    McpLogicalTool.SPLUNK_RUN_QUERY,
                    {"query": spl, "earliest_time": "0", "latest_time": "now"},
                )
                ctx.correlation_summary = str(q_result)[:1000]
                ctx.tools_called.append("splunk_run_query")
            except McpToolError as e:
                ctx.notes.append("correlation query failed: {0}".format(e))

    if not ctx.tools_called:
        return None
    return ctx


def _safe_correlation_spl(normalized: Dict[str, Any], search_name: Optional[str]) -> Optional[str]:
    """Build a short, read-only correlation search from alert fields."""
    host = normalized.get("host")
    user = normalized.get("user")
    if not host and not user:
        return None
    parts = ["search index=*"]
    if host:
        parts.append('host="{0}"'.format(str(host).replace('"', '\\"')))
    if user:
        parts.append('user="{0}"'.format(str(user).replace('"', '\\"')))
    parts.append("| head 20")
    return " ".join(parts)


def merge_mcp_into_classification_signals(
    signals: List[str],
    mcp_context: Optional[McpAlertContext],
) -> List[str]:
    """Append MCP-derived hints for classifier transparency."""
    if mcp_context is None:
        return signals
    extra = list(signals)
    if mcp_context.metadata_hosts:
        extra.append("mcp_host_context")
    if mcp_context.metadata_sourcetypes:
        extra.append("mcp_sourcetype_context")
    if mcp_context.correlation_summary:
        extra.append("mcp_correlation")
    return sorted(set(extra))
