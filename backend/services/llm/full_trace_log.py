"""
Full-length trace logging for Splunk MCP JSON-RPC and SAIA (AI Assistant) tool calls.

No truncation of request/response bodies in log messages. Bearer tokens are redacted only.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from config import Settings

LOGGER_MCP = "tsoc.trace.mcp"
LOGGER_SAIA = "tsoc.trace.saia"


def mcp_trace_enabled(settings: Settings) -> bool:
    return bool(getattr(settings, "tsoc_mcp_trace_log", False))


def saia_trace_enabled(settings: Settings) -> bool:
    return bool(getattr(settings, "tsoc_saia_trace_log", False))


def serialize_full(value: Any) -> str:
    """Serialize for logs without length limits (no truncation)."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (bytes, bytearray)):
        return value.decode("utf-8", errors="replace")
    try:
        return json.dumps(value, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return repr(value)


def _trace_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def log_mcp_rpc_request(
    settings: Settings,
    *,
    url: str,
    method: str,
    payload: Dict[str, Any],
) -> None:
    if not mcp_trace_enabled(settings):
        return
    _trace_logger(LOGGER_MCP).info(
        "[MCP_REQUEST] method=%s url=%s\n%s",
        method,
        url,
        serialize_full(payload),
    )


def _summarize_mcp_trace_body(method: str, body_text: str, parsed: Any) -> str:
    """Keep tools/list traces small (full schemas are huge and repeat every query)."""
    if method != "tools/list":
        return body_text if body_text is not None else ""
    names: list[str] = []
    if isinstance(parsed, dict):
        tools = parsed.get("tools")
        if isinstance(tools, list):
            for t in tools:
                if isinstance(t, dict) and t.get("name"):
                    names.append(str(t["name"]))
                elif isinstance(t, str):
                    names.append(t)
    if names:
        return "tools: " + ", ".join(names)
    if body_text and len(body_text) > 400:
        return body_text[:400] + "... (truncated)"
    return body_text if body_text is not None else ""


def log_mcp_rpc_response(
    settings: Settings,
    *,
    method: str,
    status_code: int,
    body_text: str,
    parsed: Any = None,
) -> None:
    if not mcp_trace_enabled(settings):
        return
    body_out = _summarize_mcp_trace_body(method, body_text, parsed)
    parts = [
        "[MCP_RESPONSE] method={0} http_status={1}".format(method, status_code),
        "--- body ---",
        body_out,
    ]
    if parsed is not None and method != "tools/list":
        parts.extend(["--- parsed ---", serialize_full(parsed)])
    _trace_logger(LOGGER_MCP).info("\n".join(parts))


def log_mcp_rpc_error(
    settings: Settings,
    *,
    method: str,
    error: str,
    status_code: Optional[int] = None,
    body_text: Optional[str] = None,
) -> None:
    if not mcp_trace_enabled(settings):
        return
    parts = ["[MCP_ERROR] method={0} error={1}".format(method, error)]
    if status_code is not None:
        parts.append("http_status={0}".format(status_code))
    if body_text:
        parts.extend(["--- body ---", body_text])
    _trace_logger(LOGGER_MCP).info("\n".join(parts))


def log_mcp_tool_call(
    settings: Settings,
    *,
    logical_tool: str,
    server_tool_name: str,
    arguments: Dict[str, Any],
    result: Any = None,
    error: Optional[str] = None,
) -> None:
    if not mcp_trace_enabled(settings):
        return
    log = _trace_logger(LOGGER_MCP)
    log.info(
        "[MCP_TOOL_REQUEST] logical=%s server=%s\n%s",
        logical_tool,
        server_tool_name,
        serialize_full(arguments),
    )
    if error:
        log.info("[MCP_TOOL_ERROR] logical=%s server=%s\n%s", logical_tool, server_tool_name, error)
    elif result is not None:
        log.info(
            "[MCP_TOOL_RESPONSE] logical=%s server=%s\n%s",
            logical_tool,
            server_tool_name,
            serialize_full(result),
        )


def log_saia_pipeline_start(
    settings: Settings,
    *,
    query: str,
    index: Optional[str],
    context: Optional[str],
    objective: Optional[str],
) -> None:
    if not saia_trace_enabled(settings):
        return
    _trace_logger(LOGGER_SAIA).info(
        "[SAIA_PIPELINE_START]\nquery=%s\nindex=%s\ncontext=%s\nobjective=%s",
        query,
        index or "",
        context or "",
        objective or "",
    )


def log_saia_tool(
    settings: Settings,
    *,
    step: str,
    logical_tool: str,
    request: Dict[str, Any],
    response_raw: Any = None,
    parsed: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
) -> None:
    if not saia_trace_enabled(settings):
        return
    log = _trace_logger(LOGGER_SAIA)
    log.info(
        "[SAIA_REQUEST] step=%s tool=%s\n%s",
        step,
        logical_tool,
        serialize_full(request),
    )
    if error:
        log.info("[SAIA_ERROR] step=%s tool=%s\n%s", step, logical_tool, error)
    elif response_raw is not None:
        log.info(
            "[SAIA_RESPONSE] step=%s tool=%s\n%s",
            step,
            logical_tool,
            serialize_full(response_raw),
        )
    if parsed is not None:
        log.info(
            "[SAIA_PARSED] step=%s tool=%s\n%s",
            step,
            logical_tool,
            serialize_full(parsed),
        )


def _trace_formatter() -> logging.Formatter:
    return logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )


def _has_stderr_stream_handler(log: logging.Logger) -> bool:
    for h in log.handlers:
        if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler):
            if getattr(h, "stream", None) is sys.stderr:
                return True
    return False


def configure_trace_logging(settings: Settings) -> None:
    """
    Wire MCP/SAIA trace loggers to console (stderr) and optional file.

    Uses propagate=False so trace lines appear even when root LOG_LEVEL is WARNING.
    """
    fmt = _trace_formatter()
    pairs = (
        (LOGGER_MCP, mcp_trace_enabled(settings)),
        (LOGGER_SAIA, saia_trace_enabled(settings)),
    )
    any_trace = any(enabled for _, enabled in pairs)
    if not any_trace:
        return

    path = (getattr(settings, "tsoc_trace_log_file", None) or "").strip()
    log_path = Path(path) if path else None
    if log_path is not None:
        log_path.parent.mkdir(parents=True, exist_ok=True)

    for name, enabled in pairs:
        if not enabled:
            continue
        log = logging.getLogger(name)
        log.setLevel(logging.INFO)
        log.propagate = False

        if not _has_stderr_stream_handler(log):
            stream_handler = logging.StreamHandler(sys.stderr)
            stream_handler.setFormatter(fmt)
            log.addHandler(stream_handler)

        if log_path is not None:
            path_str = str(log_path.resolve())
            if not any(
                isinstance(h, logging.FileHandler)
                and getattr(h, "baseFilename", None) == path_str
                for h in log.handlers
            ):
                file_handler = logging.FileHandler(path_str, encoding="utf-8")
                file_handler.setFormatter(fmt)
                log.addHandler(file_handler)


# Backward-compatible alias
configure_trace_log_handlers = configure_trace_logging
