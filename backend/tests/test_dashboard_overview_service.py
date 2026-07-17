"""Dashboard overview builder performance and integration probes."""

from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, patch

import pytest

from config import Settings
from models.mcp import McpStatusResponse
from services.platform import dashboard_overview as mod
from services.platform.dashboard_overview import (
    _integrations_status,
    build_dashboard_overview,
)


@pytest.fixture(autouse=True)
def clear_integrations_cache() -> None:
    mod._integrations_cache = None
    yield
    mod._integrations_cache = None


@pytest.mark.asyncio
async def test_integrations_status_uses_cache(test_settings_with_ingest_token: Settings) -> None:
    settings = test_settings_with_ingest_token.model_copy(
        update={"tsoc_postgres_dsn": "postgresql://test"}
    )
    mcp = McpStatusResponse(configured=False, connected=False)

    with patch(
        "services.platform.dashboard_overview._mcp_status_for_dashboard",
        new_callable=AsyncMock,
        return_value=mcp,
    ) as mcp_mock, patch(
        "services.platform.dashboard_overview._neo4j_reachable_bounded",
        new_callable=AsyncMock,
        return_value=False,
    ) as neo_mock:
        first = await _integrations_status(settings)
        second = await _integrations_status(settings)

    assert first.mcp is False
    assert second == first
    mcp_mock.assert_awaited_once()
    neo_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_mcp_status_for_dashboard_times_out(test_settings_with_ingest_token: Settings) -> None:
    settings = test_settings_with_ingest_token.model_copy(
        update={"tsoc_mcp_enabled": True, "splunk_mcp_token": "tok"}
    )

    async def slow_status(_settings: Settings) -> McpStatusResponse:
        await asyncio.sleep(5)
        return McpStatusResponse(configured=True, connected=True)

    original_timeout = mod._MCP_PROBE_TIMEOUT_SECONDS
    mod._MCP_PROBE_TIMEOUT_SECONDS = 0.05
    try:
        with patch(
            "services.platform.dashboard_overview.get_mcp_status",
            new_callable=AsyncMock,
            side_effect=slow_status,
        ):
            status = await mod._mcp_status_for_dashboard(settings)
    finally:
        mod._MCP_PROBE_TIMEOUT_SECONDS = original_timeout

    assert status.configured is True
    assert status.connected is False
    assert "timed out" in (status.message or "").lower()


@pytest.mark.asyncio
async def test_build_dashboard_overview_parallel_fetch(
    test_settings_with_ingest_token: Settings,
) -> None:
    settings = test_settings_with_ingest_token.model_copy(
        update={"tsoc_postgres_dsn": "postgresql://test"}
    )

    async def slow_int(_settings: Settings):
        await asyncio.sleep(0.05)
        from models.dashboard import DashboardIntegrations

        return DashboardIntegrations(postgres=True, llm=False, mcp=False, neo4j=False)

    async def slow_ints(_settings: Settings) -> int:
        await asyncio.sleep(0.05)
        return 1

    async def slow_inv(_settings: Settings) -> tuple[int, int]:
        await asyncio.sleep(0.05)
        return 2, 3

    async def slow_list(_settings: Settings, **_kwargs: object) -> list:
        await asyncio.sleep(0.05)
        return []

    async def slow_triage(_settings: Settings) -> list:
        await asyncio.sleep(0.05)
        return []

    async def slow_runbook_ops(_settings: Settings) -> dict:
        await asyncio.sleep(0.05)
        return {
            "latest_runbooks": 4,
            "source_verified": 3,
            "human_approved": 2,
            "reused": 1,
            "evidence_rows": 6,
        }

    with patch(
        "services.platform.dashboard_overview.splunk_store_configured",
        return_value=True,
    ), patch(
        "services.platform.dashboard_overview._integrations_status",
        side_effect=slow_int,
    ), patch(
        "services.platform.dashboard_overview.fetch_total_records",
        side_effect=slow_ints,
    ), patch(
        "services.platform.dashboard_overview.fetch_analyses_last_24h",
        side_effect=slow_ints,
    ), patch(
        "services.platform.dashboard_overview.fetch_inventory_counts",
        side_effect=slow_inv,
    ), patch(
        "services.platform.dashboard_overview.fetch_record_counts_by_type",
        side_effect=slow_list,
    ), patch(
        "services.platform.dashboard_overview.fetch_activity_by_day",
        side_effect=slow_list,
    ), patch(
        "services.platform.dashboard_overview._collect_triage_items",
        side_effect=slow_triage,
    ), patch(
        "services.platform.dashboard_overview.fetch_runbook_ops",
        side_effect=slow_runbook_ops,
    ):
        t0 = time.perf_counter()
        overview = await build_dashboard_overview(settings)
        elapsed = time.perf_counter() - t0

    assert overview.kpis.total_records == 1
    assert overview.kpis.users == 2
    assert overview.runbook_ops.latest_runbooks == 4
    assert overview.runbook_ops.human_approved == 2
    assert overview.runbook_ops.evidence_rows == 6
    assert elapsed < 0.25
