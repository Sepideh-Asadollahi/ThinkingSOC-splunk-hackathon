"""MCP status API tests."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from config import get_settings
from main import app
from services.splunk_integration.splunk_mcp_service import get_mcp_status


@pytest.mark.asyncio
async def test_mcp_status_not_configured():
    settings = get_settings()
    settings.tsoc_mcp_enabled = False
    settings.splunk_mcp_token = None
    status = await get_mcp_status(settings)
    assert status.configured is False
    assert status.connected is False


@pytest.mark.asyncio
async def test_mcp_status_http_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/api/v1/mcp/status")
        assert r.status_code == 200
        data = r.json()
        assert "configured" in data
        assert "tools" in data
