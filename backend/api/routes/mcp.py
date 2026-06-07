from __future__ import annotations

import logging
import time

from fastapi import APIRouter, Depends, HTTPException, Request

from api.http_rid import http_rid
from api.deps import check_ingest_bearer
from config import Settings, get_settings, mcp_configured
from models.mcp import (
    McpSplGenerateRequest,
    McpSplGenerateResponse,
    McpStatusResponse,
    McpToolCallRequest,
    McpToolCallResponse,
)
from services.splunk_integration.splunk_mcp_service import get_mcp_status
from splunk.mcp.client import SplunkMcpClient
from splunk.mcp.errors import McpNotConfiguredError, McpToolError
from splunk.mcp.spl_assistant import generate_spl_via_mcp

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/mcp/status", response_model=McpStatusResponse)
async def mcp_status_endpoint(
    settings: Settings = Depends(get_settings),
) -> McpStatusResponse:
    """Splunk MCP Server connectivity and tool inventory (for judges and operators)."""
    return await get_mcp_status(settings)


@router.post(
    "/mcp/spl-generate",
    dependencies=[Depends(check_ingest_bearer)],
    response_model=McpSplGenerateResponse,
)
async def mcp_spl_generate_endpoint(
    request: Request,
    body: McpSplGenerateRequest,
    settings: Settings = Depends(get_settings),
) -> McpSplGenerateResponse:
    """Generate, optimize, and explain SPL via Splunk MCP SAIA tools."""
    t0 = time.perf_counter()
    if not mcp_configured(settings):
        raise HTTPException(status_code=503, detail="Splunk MCP is not configured")
    try:
        rc, raw = await generate_spl_via_mcp(
            settings,
            query=body.query,
            index=body.index,
            context=body.context,
            objective=body.context,
        )
    except McpNotConfiguredError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except McpToolError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    if rc is None:
        logger.info(
            "api POST /mcp/spl-generate rid=%s unavailable duration_ms=%.1f",
            http_rid(request),
            (time.perf_counter() - t0) * 1000.0,
        )
        return McpSplGenerateResponse(source="unavailable", raw=raw)

    logger.info(
        "api POST /mcp/spl-generate rid=%s ok spl_len=%d duration_ms=%.1f",
        http_rid(request),
        len(rc.spl or ""),
        (time.perf_counter() - t0) * 1000.0,
    )
    return McpSplGenerateResponse(
        source="splunk_mcp_saia",
        spl=rc.spl,
        explanation=rc.explanation,
        raw=raw,
    )


@router.post(
    "/mcp/tools/call",
    dependencies=[Depends(check_ingest_bearer)],
    response_model=McpToolCallResponse,
)
async def mcp_tool_call_endpoint(
    request: Request,
    body: McpToolCallRequest,
    settings: Settings = Depends(get_settings),
) -> McpToolCallResponse:
    """Debug/demo: invoke any MCP tool by exact name."""
    if not mcp_configured(settings):
        raise HTTPException(status_code=503, detail="Splunk MCP is not configured")
    try:
        client = SplunkMcpClient(settings)
        result = await client.call_tool_by_name(body.tool_name, body.arguments)
    except McpNotConfiguredError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except McpToolError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    logger.info(
        "api POST /mcp/tools/call rid=%s tool=%s",
        http_rid(request),
        body.tool_name,
    )
    return McpToolCallResponse(tool_name=body.tool_name, result=result)
