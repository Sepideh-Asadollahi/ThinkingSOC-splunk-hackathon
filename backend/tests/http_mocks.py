"""Shared HTTP mock helpers for unit tests."""

from __future__ import annotations

from typing import Any

import httpx


def mock_httpx_json_response(
    status_code: int = 200,
    *,
    json_body: dict[str, Any] | None = None,
    text: str = "",
    url: str = "https://splunk.test/services/mcp",
) -> httpx.Response:
    """Build an httpx.Response with request bound (required for raise_for_status)."""
    request = httpx.Request("POST", url)
    if json_body is not None:
        return httpx.Response(status_code, json=json_body, request=request)
    return httpx.Response(status_code, text=text, request=request)
