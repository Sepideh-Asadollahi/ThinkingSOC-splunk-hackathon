"""Mock SplunkMcpClient._rpc for unit tests (avoids patching global httpx.AsyncClient.post)."""

from __future__ import annotations

from typing import Any, Callable


def _rpc_result(body: dict[str, Any]) -> Any:
    return body.get("result", body)


def build_mcp_rpc_mock(
    *,
    initialize: dict[str, Any],
    tools_list: dict[str, Any],
    tool_calls: list[dict[str, Any]] | None = None,
) -> Callable[..., Any]:
    """Return async mock for SplunkMcpClient._rpc with queued tools/call results."""
    pending = [_rpc_result(b) for b in (tool_calls or [])]

    async def _rpc(self, method: str, params: dict[str, Any] | None = None) -> Any:
        if method == "initialize":
            return _rpc_result(initialize)
        if method == "notifications/initialized":
            return {}
        if method == "tools/list":
            return _rpc_result(tools_list)
        if method == "tools/call":
            if not pending:
                raise RuntimeError("unexpected tools/call (no queued fixture)")
            return pending.pop(0)
        return {}

    return _rpc
