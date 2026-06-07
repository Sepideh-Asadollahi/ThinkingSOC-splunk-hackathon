"""SAIA REST /predict (UI path) + MCP ``splunk_run_query`` — shared by app and ``spl_predict_ask``."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from config import Settings, mcp_configured
from models.analysis import RootCauseSpl, SplSearchResult
from splunk.client import SplunkRestClient
from splunk.mcp.client import SplunkMcpClient
from splunk.mcp.errors import McpNotConfiguredError, McpToolError
from splunk.mcp.saia.parse import extract_spl_from_saia_text
from splunk.mcp.tool_registry import McpLogicalTool, resolve_tool_name

logger = logging.getLogger(__name__)

# Splunk best practice (Search Reference): All time in SPL = earliest=1 latest=now
# REST/MCP job params: earliest_time=0 latest_time=now (alltime window)
REST_ALL_TIME_EARLIEST = "0"
REST_ALL_TIME_LATEST = "now"
SPL_ALL_TIME_WINDOW = "earliest=1 latest=now"
ALL_TIME_EARLIEST = REST_ALL_TIME_EARLIEST
ALL_TIME_LATEST = REST_ALL_TIME_LATEST
_DEFAULT_EXECUTE_MAX_ROWS = 50

# Generic syntax helpers (single source of truth: spl_syntax_sanitize).
from services.investigation.spl_syntax_sanitize import (
    discourage_values_aggregation,
    fix_spl_quoted_string_escapes,
    quote_spl_colon_field_values,
    sanitize_spl_syntax,
    strip_time_range_from_spl,
)


def default_investigation_time_window(settings: Settings) -> str:
    """Always All Time (ignores ``tsoc_investigation_spl_time_window``)."""
    _ = settings
    return SPL_ALL_TIME_WINDOW


def normalize_execution_time_window(time_window: Optional[str] = None) -> str:
    """Force stored/executed job bounds to All Time."""
    _ = time_window
    return SPL_ALL_TIME_WINDOW


def parse_time_window(tw: str) -> Tuple[Optional[str], Optional[str]]:
    _ = tw
    return ALL_TIME_EARLIEST, ALL_TIME_LATEST


def all_time_bounds(settings: Settings) -> Tuple[str, str]:
    _ = settings
    return ALL_TIME_EARLIEST, ALL_TIME_LATEST


def build_predict_prompt(
    *,
    objective: Optional[str] = None,
    search_name: Optional[str] = None,
    normalized: Optional[Dict[str, Any]] = None,
    splunk_results: Optional[List[Dict[str, Any]]] = None,
) -> str:
    from services.investigation.investigation_question_context import (
        format_alert_fields_block,
        merge_alert_field_sample,
        primary_alert_fields,
    )

    parts: List[str] = []
    if objective:
        parts.append(str(objective).strip())
    else:
        parts.append("Generate SPL for root-cause investigation.")
    if search_name:
        parts.append("Search name: {0}".format(search_name))
    sample = merge_alert_field_sample(normalized or {}, splunk_results)
    fields = primary_alert_fields(sample, search_name=search_name or "")
    if fields:
        parts.append(
            "Use these alert search field values in filters (do not invent hosts/users):\n"
            + format_alert_fields_block(fields, search_name=search_name or "")
        )
    elif normalized:
        parts.append("Alert fields: {0}".format(normalized))
    parts.append(
        "Do not add earliest= or latest= (or any time range) to the SPL; time bounds are applied at execution."
    )
    parts.append("Return runnable SPL.")
    return "\n".join(parts)


def _extract_predict_error_detail(exc: Exception) -> str:
    text = str(exc or "").strip()
    for marker in ('body={"', "HTTP 500): ", "HTTP 502): ", "HTTP 503): ", "HTTP 429): "):
        idx = text.find(marker)
        if idx < 0:
            continue
        fragment = text[idx:]
        start = fragment.find('{"')
        if start >= 0:
            try:
                end = fragment.rfind("}")
                if end > start:
                    data = json.loads(fragment[start : end + 1])
                    if isinstance(data, dict) and data.get("error"):
                        return str(data["error"]).strip()
            except json.JSONDecodeError:
                pass
        if ": " in fragment:
            return fragment.split(": ", 1)[-1].strip()[:500]
    return text[:500]


def classify_saia_predict_failure(exc: Exception) -> Tuple[str, str, str]:
    """
    Classify Splunk AI Assistant /predict failures for operator-friendly logs.

    Returns (category, short_reason, operator_hint).
    """
    detail = _extract_predict_error_detail(exc).lower()
    full = str(exc or "").lower()

    if "metering" in detail or "throttling" in detail:
        return (
            "saia_metering",
            "Splunk AI Assistant metering/throttling check failed (Splunk Cloud side)",
            "Transient Splunk platform issue. Analysis continues with LiteLLM SPL. "
            "Retry later or set TSOC_SPL_USE_REST_PREDICT=false to skip SAIA for demos.",
        )
    if "scs configs are not available" in detail or (
        "referenced before assignment" in full and "configs" in full
    ):
        return (
            "saia_config",
            "Splunk AI Assistant cloud configuration is missing or invalid",
            "Check Splunk AI Assistant app tenant/SCS token, or enable TSOC_SAIA_AUTO_REPAIR.",
        )
    if "401" in full or "403" in full or "unauthorized" in detail or "forbidden" in detail:
        return (
            "saia_auth",
            "Splunk REST authentication failed for Splunk AI Assistant /predict",
            "Verify SPLUNK_USERNAME and SPLUNK_PASSWORD and SAIA app permissions.",
        )
    if "429" in full or "rate limit" in detail or "too many requests" in detail:
        return (
            "saia_rate_limit",
            "Splunk AI Assistant rate limit reached",
            "Wait and retry, or use LiteLLM fallback (TSOC_SPL_USE_REST_PREDICT=false).",
        )
    if "502" in full or "503" in full or "service unavailable" in detail:
        return (
            "saia_unavailable",
            "Splunk AI Assistant service temporarily unavailable",
            "Transient Splunk issue. Analysis continues with LiteLLM SPL.",
        )
    if "timeout" in detail or "timed out" in detail:
        return (
            "saia_timeout",
            "Splunk AI Assistant /predict timed out",
            "Increase TSOC_SPL_PREDICT_TIMEOUT_SECONDS or use LiteLLM fallback.",
        )
    return (
        "saia_unknown",
        _extract_predict_error_detail(exc) or "Splunk AI Assistant /predict failed",
        "Analysis continues with LiteLLM SPL. See splunk_ai_assistant.log for details.",
    )


def log_saia_predict_unavailable(exc: Exception, *, after_repair: bool = False) -> None:
    category, reason, hint = classify_saia_predict_failure(exc)
    repair_note = " after auto-repair" if after_repair else ""
    logger.info(
        "investigation_spl SAIA /predict unavailable%s category=%s reason=%s "
        "next_step=litellm_spl not_an_analysis_failure=true hint=%s",
        repair_note,
        category,
        reason,
        hint,
    )


async def generate_spl_via_predict(
    settings: Settings,
    *,
    prompt: str,
    timeout_seconds: Optional[float] = None,
    poll_interval_seconds: Optional[float] = None,
) -> Optional[RootCauseSpl]:
    """Generate SPL via Splunk AI Assistant REST ``/predict`` (same path as UI chat)."""
    if not settings.splunk_username or not settings.splunk_password:
        return None
    client = SplunkRestClient(settings)
    t_out = timeout_seconds if timeout_seconds is not None else float(
        getattr(settings, "tsoc_spl_predict_timeout_seconds", 90.0)
    )
    poll_iv = poll_interval_seconds if poll_interval_seconds is not None else float(
        getattr(settings, "tsoc_spl_predict_poll_interval_seconds", 0.75)
    )
    session_key = await client.login()
    try:
        raw = await client.predict_spl_via_ui_path(
            session_key,
            prompt=prompt.strip(),
            timeout_seconds=t_out,
            poll_interval_seconds=poll_iv,
        )
    except Exception as e:
        from splunk.saia_config_repair import ensure_saia_cloud_configs, is_saia_configs_repair_error

        if is_saia_configs_repair_error(e) and await ensure_saia_cloud_configs(
            settings, session_key=session_key
        ):
            try:
                raw = await client.predict_spl_via_ui_path(
                    session_key,
                    prompt=prompt.strip(),
                    timeout_seconds=t_out,
                    poll_interval_seconds=poll_iv,
                )
            except Exception as retry_err:
                log_saia_predict_unavailable(retry_err, after_repair=True)
                return None
        else:
            log_saia_predict_unavailable(e)
            return None
    spl = extract_spl_from_saia_text(raw) or str(raw or "").strip()
    if not spl:
        return None
    return RootCauseSpl(
        spl=spl,
        explanation="Generated via Splunk UI REST /predict path.",
        time_window=SPL_ALL_TIME_WINDOW,
        notes=["rest_predict_write_spl"],
    )


def rows_from_mcp_result(raw: Any) -> List[Dict[str, Any]]:
    if isinstance(raw, list):
        return [x for x in raw if isinstance(x, dict)]
    if isinstance(raw, dict):
        for key in ("results", "rows", "data"):
            val = raw.get(key)
            if isinstance(val, list):
                return [x for x in val if isinstance(x, dict)]
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
            return rows_from_mcp_result(parsed)
        except json.JSONDecodeError:
            return []
    return []


def parse_mcp_execute_result(raw: Any) -> Tuple[List[Dict[str, Any]], Optional[int], bool]:
    rows = rows_from_mcp_result(raw)
    total_rows: Optional[int] = None
    mcp_truncated = False
    if isinstance(raw, dict):
        tr = raw.get("total_rows")
        if tr is not None:
            try:
                total_rows = int(tr)
            except (TypeError, ValueError):
                pass
        mcp_truncated = bool(raw.get("truncated"))
    return rows, total_rows, mcp_truncated


async def execute_spl_via_mcp(
    settings: Settings,
    spl: str,
    *,
    row_limit: Optional[int] = None,
    earliest_time: Optional[str] = None,
    latest_time: Optional[str] = None,
    mcp_client: Optional[SplunkMcpClient] = None,
) -> SplSearchResult:
    """Run SPL through MCP ``splunk_run_query`` (always All Time)."""
    _ = earliest_time, latest_time
    from services.investigation.spl_tstats_sanitize import sanitize_spl_draft

    spl = sanitize_spl_draft((spl or "").strip())
    if not spl:
        return SplSearchResult(row_count=0, rows=[], error="empty SPL")

    cap = row_limit if row_limit is not None else _DEFAULT_EXECUTE_MAX_ROWS
    cap = max(1, min(1000, cap))
    e = ALL_TIME_EARLIEST
    l = ALL_TIME_LATEST

    if not mcp_configured(settings):
        return SplSearchResult(row_count=0, rows=[], error="MCP not configured")

    try:
        client = mcp_client or SplunkMcpClient(settings)
        await client.ensure_ready()
        if not resolve_tool_name(client.tool_names, McpLogicalTool.SPLUNK_RUN_QUERY):
            return SplSearchResult(row_count=0, rows=[], error="splunk_run_query not available")

        raw = await client.call_tool(
            McpLogicalTool.SPLUNK_RUN_QUERY,
            {
                "query": spl,
                "earliest_time": e,
                "latest_time": l,
                "row_limit": cap,
            },
        )
        rows, total_rows, mcp_truncated = parse_mcp_execute_result(raw)
        total = total_rows if total_rows is not None else len(rows)
        capped = rows[:cap]
        return SplSearchResult(
            row_count=total,
            rows=capped,
            truncated=mcp_truncated or total > len(capped),
            error=None,
        )
    except (McpNotConfiguredError, McpToolError) as e:
        return SplSearchResult(row_count=0, rows=[], error=str(e))
    except Exception as e:
        logger.info("execute_spl_via_mcp failed spl_len=%d: %s", len(spl), e)
        return SplSearchResult(row_count=0, rows=[], error=str(e))

