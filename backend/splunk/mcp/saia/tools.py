"""Low-level SAIA MCP tool calls (generate, optimize, explain)."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple

from models.analysis import RootCauseSpl
from services.llm.full_trace_log import log_saia_tool
from services.soc_analysis.soc_analysis_root_cause_spl import sanitize_root_cause_spl_output

from ..client import SplunkMcpClient
from ..errors import McpToolError
from ..tool_registry import McpLogicalTool, resolve_tool_name
from .helpers import append_note, guess_time_window, saia_tool_args_spl
from .parse import parse_explain_text, parse_saia_spl_result
from .prompt import build_saia_generate_args

logger = logging.getLogger(__name__)


async def call_saia_generate(
    client: SplunkMcpClient,
    *,
    args: Optional[Dict[str, Any]] = None,
    normalized: Optional[Dict[str, Any]] = None,
    search_name: Optional[str] = None,
    objective: Optional[str] = None,
    cim_schema_summary: str = "",
    datamodel: Optional[str] = None,
    index: Optional[str] = None,
    context: Optional[str] = None,
) -> Tuple[Optional[RootCauseSpl], Any]:
    settings = client.settings
    if args is None:
        args = build_saia_generate_args(
            settings,
            normalized=normalized or {},
            search_name=search_name,
            objective=objective,
            cim_schema_summary=cim_schema_summary,
            datamodel=datamodel,
            index=index,
            context=context,
        )
    if not (args.get("prompt") or "").strip():
        return None, {"error": "empty prompt"}
    log_saia_tool(
        settings,
        step="generate",
        logical_tool=McpLogicalTool.SAIA_GENERATE_SPL.value,
        request=args,
    )
    try:
        raw = await client.call_tool(McpLogicalTool.SAIA_GENERATE_SPL, args)
    except McpToolError as e:
        log_saia_tool(
            settings,
            step="generate",
            logical_tool=McpLogicalTool.SAIA_GENERATE_SPL.value,
            request=args,
            error=str(e),
        )
        raise
    spl_text, explanation = parse_saia_spl_result(raw)
    log_saia_tool(
        settings,
        step="generate",
        logical_tool=McpLogicalTool.SAIA_GENERATE_SPL.value,
        request=args,
        response_raw=raw,
        parsed={"spl": spl_text, "explanation": explanation},
    )
    if not spl_text or not spl_text.strip():
        return None, raw
    llm_json: Dict[str, Any] = {
        "spl": spl_text.strip(),
        "explanation": explanation or "",
        "time_window": guess_time_window(spl_text),
        "pivots": [],
        "notes": ["mcp_saia_generate_spl"],
    }
    rc = sanitize_root_cause_spl_output(llm_json)
    if rc is None:
        rc = RootCauseSpl(spl=spl_text.strip(), explanation=explanation or "")
    append_note(rc, "mcp_saia_generate_spl")
    return rc, raw


async def call_saia_optimize(
    client: SplunkMcpClient,
    rc: RootCauseSpl,
    *,
    search_name: Optional[str],
) -> bool:
    if not resolve_tool_name(client.tool_names, McpLogicalTool.SAIA_OPTIMIZE_SPL):
        return False
    from services.llm.llm_context_budget import saia_aux_context_max_chars

    settings = client.settings
    aux_cap = saia_aux_context_max_chars(settings)
    opt_args = saia_tool_args_spl(rc.spl, search_name=search_name, aux_max_chars=aux_cap)
    log_saia_tool(
        settings,
        step="optimize",
        logical_tool=McpLogicalTool.SAIA_OPTIMIZE_SPL.value,
        request=opt_args,
    )
    try:
        raw = await client.call_tool(McpLogicalTool.SAIA_OPTIMIZE_SPL, opt_args)
        optimized, _ = parse_saia_spl_result(raw)
        log_saia_tool(
            settings,
            step="optimize",
            logical_tool=McpLogicalTool.SAIA_OPTIMIZE_SPL.value,
            request=opt_args,
            response_raw=raw,
            parsed={"optimized_spl": optimized},
        )
        if optimized and optimized.strip():
            opt = optimized.strip()
            looks_like_spl = "|" in opt or opt.lower().startswith("search ")
            if looks_like_spl and opt != rc.spl:
                rc.spl = opt
                rc.time_window = guess_time_window(rc.spl) or rc.time_window
                append_note(rc, "mcp_saia_optimize_spl")
                return True
    except McpToolError as e:
        log_saia_tool(
            settings,
            step="optimize",
            logical_tool=McpLogicalTool.SAIA_OPTIMIZE_SPL.value,
            request=opt_args,
            error=str(e),
        )
        logger.warning("saia_optimize_spl failed: %s", e)
    return False


async def call_saia_explain(
    client: SplunkMcpClient,
    rc: RootCauseSpl,
    *,
    search_name: Optional[str],
    objective: Optional[str],
) -> bool:
    if not resolve_tool_name(client.tool_names, McpLogicalTool.SAIA_EXPLAIN_SPL):
        return False
    settings = client.settings
    from services.llm.llm_context_budget import saia_aux_context_max_chars

    aux_cap = saia_aux_context_max_chars(settings)
    explain_args = saia_tool_args_spl(
        rc.spl,
        search_name=search_name,
        extra_context=objective,
        aux_max_chars=aux_cap,
    )
    log_saia_tool(
        settings,
        step="explain",
        logical_tool=McpLogicalTool.SAIA_EXPLAIN_SPL.value,
        request=explain_args,
    )
    try:
        raw = await client.call_tool(McpLogicalTool.SAIA_EXPLAIN_SPL, explain_args)
        explained = parse_explain_text(raw)
        log_saia_tool(
            settings,
            step="explain",
            logical_tool=McpLogicalTool.SAIA_EXPLAIN_SPL.value,
            request=explain_args,
            response_raw=raw,
            parsed={"explanation": explained},
        )
        if explained:
            rc.explanation = explained
            append_note(rc, "mcp_saia_explain_spl")
            return True
    except McpToolError as e:
        log_saia_tool(
            settings,
            step="explain",
            logical_tool=McpLogicalTool.SAIA_EXPLAIN_SPL.value,
            request=explain_args,
            error=str(e),
        )
        logger.warning("saia_explain_spl failed: %s", e)
    return False
