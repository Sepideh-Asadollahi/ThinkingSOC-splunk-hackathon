"""JSON-RPC client for Splunk MCP Server (HTTP, /services/mcp)."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

import httpx

from config import Settings, mcp_configured, splunk_mcp_url_for
from services.llm.full_trace_log import (
    log_mcp_rpc_error,
    log_mcp_rpc_request,
    log_mcp_rpc_response,
    log_mcp_tool_call,
    serialize_full,
)

from .errors import McpConnectionError, McpNotConfiguredError, McpToolError
from .tool_registry import McpLogicalTool, resolve_tool_name

logger = logging.getLogger(__name__)

# Splunk persistent REST handlers are sensitive to concurrent keep-alive traffic.
_mcp_transport_lock = asyncio.Lock()
_MCP_RETRY_STATUSES = frozenset({500, 502, 503, 429})
_MCP_MAX_ATTEMPTS = 3


class SplunkMcpClient:
    """Thin async client for Splunk MCP Server JSON-RPC over HTTP."""

    def __init__(self, settings: Settings) -> None:
        if not mcp_configured(settings):
            raise McpNotConfiguredError("Splunk MCP is not configured (TSOC_MCP_ENABLED, URL, token)")
        self._settings = settings
        self._url = splunk_mcp_url_for(settings)
        self._token = (settings.splunk_mcp_token or "").strip()
        self._verify = settings.splunk_mcp_verify_ssl
        self._timeout = settings.splunk_mcp_timeout_seconds
        self._req_id = 0
        self._initialized = False
        self._server_info: Dict[str, Any] = {}
        self._tools: List[str] = []
        self._http: Optional[httpx.AsyncClient] = None

    def _next_id(self) -> int:
        self._req_id += 1
        return self._req_id

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": "Bearer {0}".format(self._token),
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Connection": "close",
        }

    async def _get_http(self) -> httpx.AsyncClient:
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(
                verify=self._verify,
                timeout=self._timeout,
                limits=httpx.Limits(max_keepalive_connections=0),
            )
        return self._http

    async def aclose(self) -> None:
        if self._http is not None and not self._http.is_closed:
            await self._http.aclose()
        self._http = None

    async def _post_json(self, payload: Dict[str, Any]) -> httpx.Response:
        body_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        headers = self._headers()
        last_error: Optional[Exception] = None
        async with _mcp_transport_lock:
            for attempt in range(1, _MCP_MAX_ATTEMPTS + 1):
                try:
                    client = await self._get_http()
                    response = await client.post(self._url, headers=headers, content=body_bytes)
                    if response.status_code in _MCP_RETRY_STATUSES and attempt < _MCP_MAX_ATTEMPTS:
                        logger.warning(
                            "mcp rpc HTTP %s attempt=%d/%d (will retry)",
                            response.status_code,
                            attempt,
                            _MCP_MAX_ATTEMPTS,
                        )
                        await asyncio.sleep(0.5 * attempt)
                        await self.aclose()
                        continue
                    return response
                except httpx.RequestError as exc:
                    last_error = exc
                    if attempt < _MCP_MAX_ATTEMPTS:
                        logger.warning(
                            "mcp rpc transport error attempt=%d/%d: %s (will retry)",
                            attempt,
                            _MCP_MAX_ATTEMPTS,
                            exc,
                        )
                        await asyncio.sleep(0.5 * attempt)
                        await self.aclose()
                        continue
                    raise
        if last_error is not None:
            raise last_error
        raise McpConnectionError("MCP RPC failed after retries")

    async def _notify(self, method: str) -> None:
        """Send an MCP notification (no JSON-RPC id, no response expected)."""
        payload: Dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        log_mcp_rpc_request(self._settings, url=self._url, method=method, payload=payload)
        try:
            response = await self._post_json(payload)
            log_mcp_rpc_response(
                self._settings,
                method=method,
                status_code=response.status_code,
                body_text=response.text if response.text is not None else "",
            )
        except Exception as exc:
            log_mcp_rpc_error(self._settings, method=method, error=str(exc))

    async def _rpc(self, method: str, params: Optional[Dict[str, Any]] = None) -> Any:
        payload: Dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": method,
        }
        if params is not None:
            payload["params"] = params
        log_mcp_rpc_request(self._settings, url=self._url, method=method, payload=payload)
        body = ""
        status_code = 0
        try:
            response = await self._post_json(payload)
            status_code = response.status_code
            body = response.text if response.text is not None else ""
            try:
                response.raise_for_status()
            except httpx.HTTPError as e:
                log_mcp_rpc_error(
                    self._settings,
                    method=method,
                    error=str(e),
                    status_code=status_code,
                    body_text=body,
                )
                raise McpConnectionError(
                    "MCP RPC failed method={0}: {1}".format(method, e)
                ) from e
            stripped = body.strip()
            if not stripped:
                log_mcp_rpc_response(
                    self._settings,
                    method=method,
                    status_code=status_code,
                    body_text=body,
                )
                return None
            data = response.json()
        except httpx.HTTPError as e:
            log_mcp_rpc_error(self._settings, method=method, error=str(e))
            raise McpConnectionError("MCP RPC failed method={0}: {1}".format(method, e)) from e
        except ValueError as e:
            log_mcp_rpc_error(
                self._settings,
                method=method,
                error="non-JSON response: {0}".format(e),
                status_code=status_code or None,
                body_text=body,
            )
            raise McpConnectionError(
                "MCP RPC returned non-JSON for method={0}: {1}".format(method, e)
            ) from e
        log_mcp_rpc_response(
            self._settings,
            method=method,
            status_code=status_code,
            body_text=body,
            parsed=data if isinstance(data, dict) else None,
        )
        if not isinstance(data, dict):
            log_mcp_rpc_error(
                self._settings,
                method=method,
                error="response is not a JSON object",
                body_text=body,
            )
            raise McpConnectionError("MCP RPC returned non-object for method={0}".format(method))
        if data.get("error"):
            err = data["error"]
            msg = err.get("message") if isinstance(err, dict) else str(err)
            log_mcp_rpc_error(
                self._settings,
                method=method,
                error=serialize_full(data.get("error")),
                body_text=body,
            )
            raise McpToolError("MCP RPC error method={0}: {1}".format(method, msg))
        return data.get("result")

    async def initialize(self) -> Dict[str, Any]:
        """Call MCP initialize and cache server info + tool list."""
        result = await self._rpc(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "thinking-soc-hackathon", "version": "0.1.0"},
            },
        )
        self._initialized = True
        if isinstance(result, dict):
            self._server_info = dict(result.get("serverInfo") or {})
        try:
            await self._notify("notifications/initialized")
        except Exception:
            pass
        await self.refresh_tools()
        return result if isinstance(result, dict) else {}

    async def refresh_tools(self) -> List[str]:
        """Fetch tools/list and cache tool names."""
        result = await self._rpc("tools/list", {})
        names: List[str] = []
        if isinstance(result, dict):
            tools = result.get("tools")
            if isinstance(tools, list):
                for t in tools:
                    if isinstance(t, dict) and t.get("name"):
                        names.append(str(t["name"]))
                    elif isinstance(t, str):
                        names.append(t)
        self._tools = names
        return names

    @property
    def settings(self) -> Settings:
        return self._settings

    @property
    def tool_names(self) -> List[str]:
        return list(self._tools)

    @property
    def server_info(self) -> Dict[str, Any]:
        return dict(self._server_info)

    async def ensure_ready(self) -> None:
        if not self._initialized:
            await self.initialize()

    async def call_tool(self, logical: McpLogicalTool, arguments: Dict[str, Any]) -> Any:
        """Resolve logical tool name and invoke tools/call."""
        await self.ensure_ready()
        name = resolve_tool_name(self._tools, logical)
        if not name:
            raise McpToolError(
                "Tool not available on MCP server: {0}".format(logical.value),
                tool_name=logical.value,
            )
        try:
            result = await self._rpc(
                "tools/call",
                {"name": name, "arguments": arguments},
            )
        except (McpConnectionError, McpToolError) as e:
            log_mcp_tool_call(
                self._settings,
                logical_tool=logical.value,
                server_tool_name=name,
                arguments=arguments,
                error=str(e),
            )
            raise
        if isinstance(result, dict) and result.get("isError"):
            content = result.get("content")
            detail = content
            if isinstance(content, list) and content:
                first = content[0]
                if isinstance(first, dict):
                    detail = first.get("text", first)
            log_mcp_tool_call(
                self._settings,
                logical_tool=logical.value,
                server_tool_name=name,
                arguments=arguments,
                error=serialize_full(detail),
            )
            raise McpToolError("MCP tool returned error: {0}".format(detail), tool_name=name)
        unwrapped = _unwrap_tool_result(result)
        log_mcp_tool_call(
            self._settings,
            logical_tool=logical.value,
            server_tool_name=name,
            arguments=arguments,
            result=unwrapped,
        )
        return unwrapped

    async def call_tool_by_name(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Invoke a tool by exact server name (debug/demo)."""
        await self.ensure_ready()
        if name not in self._tools:
            raise McpToolError("Unknown MCP tool: {0}".format(name), tool_name=name)
        try:
            result = await self._rpc("tools/call", {"name": name, "arguments": arguments})
        except (McpConnectionError, McpToolError) as e:
            log_mcp_tool_call(
                self._settings,
                logical_tool=name,
                server_tool_name=name,
                arguments=arguments,
                error=str(e),
            )
            raise
        if isinstance(result, dict) and result.get("isError"):
            log_mcp_tool_call(
                self._settings,
                logical_tool=name,
                server_tool_name=name,
                arguments=arguments,
                error="isError in tool result",
            )
            raise McpToolError("MCP tool returned error for {0}".format(name), tool_name=name)
        unwrapped = _unwrap_tool_result(result)
        log_mcp_tool_call(
            self._settings,
            logical_tool=name,
            server_tool_name=name,
            arguments=arguments,
            result=unwrapped,
        )
        return unwrapped

    async def ping(self) -> bool:
        """Return True if initialize succeeds."""
        try:
            await self.initialize()
            return True
        except (McpConnectionError, McpToolError) as e:
            logger.warning("mcp ping failed: %s", e)
            return False


def _unwrap_tool_result(result: Any) -> Any:
    """Extract text/structured payload from MCP tools/call result."""
    if not isinstance(result, dict):
        return result
    if "structuredContent" in result and result["structuredContent"] is not None:
        return result["structuredContent"]
    content = result.get("content")
    if isinstance(content, list):
        texts: List[str] = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                texts.append(str(block.get("text", "")))
            elif isinstance(block, str):
                texts.append(block)
        if len(texts) == 1:
            return texts[0]
        if texts:
            return "\n".join(texts)
    return result
