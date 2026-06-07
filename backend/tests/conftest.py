"""Pytest fixtures: run from backend/ with pytest (PYTHONPATH via pytest.ini)."""

from __future__ import annotations

import os
from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from config import Settings, get_settings, mcp_configured
from main import app
from api.deps import reset_rate_limit_buckets


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "splunk_live: live Splunk MCP/SAIA integration (requires TSOC_RUN_SPLUNK_LIVE=1)",
    )


@pytest.fixture(autouse=True)
def clear_settings_cache() -> Generator[None, None, None]:
    get_settings.cache_clear()
    reset_rate_limit_buckets()
    yield
    reset_rate_limit_buckets()
    get_settings.cache_clear()
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def mock_app_postgres_lifecycle(request: pytest.FixtureRequest) -> Generator[None, None, None]:
    """Do not open a real DB pool during FastAPI TestClient startup/shutdown."""
    if request.node.get_closest_marker("real_startup") is not None:
        yield
        return
    with (
        patch("main.init_store", new_callable=AsyncMock),
        patch("main.close_store", new_callable=AsyncMock),
        patch("main._saia_startup", new_callable=AsyncMock),
        patch("main._rag_startup", new_callable=AsyncMock),
        patch("main.correlation_startup", new_callable=AsyncMock),
        patch("main.correlation_shutdown", new_callable=AsyncMock),
    ):
        yield


@pytest.fixture(autouse=True)
def reset_splunk_json_store_pool() -> Generator[None, None, None]:
    from services.splunk_json_store import pg as pg_store

    prev = pg_store._PG_POOL
    pg_store._PG_POOL = None
    yield
    pg_store._PG_POOL = prev


@pytest.fixture
def splunk_live_settings() -> Settings:
    """Real settings from .env for live Splunk tests."""
    if os.environ.get("TSOC_RUN_SPLUNK_LIVE") != "1":
        pytest.skip("Set TSOC_RUN_SPLUNK_LIVE=1 to run live Splunk tests")
    settings = get_settings()
    if not mcp_configured(settings):
        pytest.skip("Splunk MCP not configured (TSOC_MCP_ENABLED, SPLUNK_MCP_TOKEN)")
    if not settings.splunk_username or not settings.splunk_password:
        pytest.skip("SPLUNK_USERNAME and SPLUNK_PASSWORD required for live Splunk tests")
    return settings


@pytest.fixture
def live_api_base() -> str:
    return os.environ.get("TSOC_LIVE_API_BASE", "http://127.0.0.1:9876").rstrip("/")


@pytest.fixture
async def saia_backend_ok(splunk_live_settings: Settings) -> bool:
    """
    Probe whether Splunk AI Assistant cloud API is reachable via MCP.

    When False, SAIA tool tests are skipped (common when SAIA tenant is not provisioned).
    """
    from splunk.mcp.client import SplunkMcpClient
    from splunk.mcp.errors import McpToolError
    from splunk.mcp.tool_registry import McpLogicalTool, resolve_tool_name

    client = SplunkMcpClient(splunk_live_settings)
    await client.ensure_ready()
    if not resolve_tool_name(client.tool_names, McpLogicalTool.SAIA_GENERATE_SPL):
        return False
    try:
        await client.call_tool(
            McpLogicalTool.SAIA_GENERATE_SPL,
            {"prompt": "index=_internal | head 1", "spl_only": True},
        )
        return True
    except McpToolError as e:
        msg = str(e).lower()
        if "404" in msg or "saia-api" in msg or "not found" in msg:
            return False
        raise


@pytest.fixture
def force_soc_analysis_langgraph_fallback():
    """Force SOC analysis tests through langgraph_fallback (no live LiteLLM)."""
    with patch(
        "services.soc_analysis.runner.run_soc_analysis_langgraph",
        new_callable=AsyncMock,
    ) as m:
        m.side_effect = RuntimeError("test: LLM unavailable")
        yield m


@pytest.fixture
def test_settings() -> Settings:
    return Settings(
        splunk_mgmt_url="https://127.0.0.1:8089",
        splunk_username="",
        splunk_password="",
        splunk_verify_ssl=False,
        tsoc_mcp_enabled=False,
        splunk_mcp_url=None,
        splunk_mcp_token=None,
        tsoc_spl_use_rest_predict=False,
        tsoc_investigation_questions_max=3,
        tsoc_postgres_dsn=None,
        tsoc_ingest_auto_analyze=False,
        tsoc_ingest_token=None,
        tsoc_alert_log_path=None,
        litellm_api_key=None,
        litellm_api_base=None,
    )


@pytest.fixture
def test_settings_with_ingest_token() -> Settings:
    return Settings(
        splunk_mgmt_url="https://127.0.0.1:8089",
        splunk_username="",
        splunk_password="",
        splunk_verify_ssl=False,
        tsoc_mcp_enabled=False,
        splunk_mcp_url=None,
        splunk_mcp_token=None,
        tsoc_spl_use_rest_predict=False,
        tsoc_investigation_questions_max=3,
        tsoc_postgres_dsn=None,
        tsoc_ingest_auto_analyze=False,
        tsoc_ingest_token="expected-ingest-secret",
        litellm_api_key=None,
        litellm_api_base=None,
        tsoc_alert_log_path=None,
    )


@pytest.fixture
def client(test_settings: Settings) -> Generator[TestClient, None, None]:
    def _override() -> Settings:
        return test_settings

    app.dependency_overrides[get_settings] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def client_with_token(test_settings_with_ingest_token: Settings) -> Generator[TestClient, None, None]:
    def _override() -> Settings:
        return test_settings_with_ingest_token

    app.dependency_overrides[get_settings] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def mock_enrich_ok() -> Generator[AsyncMock, None, None]:
    async def _side_effect(*args, **kwargs):
        return {
            "splunk_results_row_count": 2,
            "splunk_results": [{"a": "1"}, {"a": "2"}],
            "splunk_job": {"entry": []},
            "handoff": {},
        }

    with patch("api.routes.ingest.enrich_alert_from_splunk", new_callable=AsyncMock) as m:
        m.side_effect = _side_effect
        yield m


@pytest.fixture
def mock_enrich_value_error() -> Generator[AsyncMock, None, None]:
    async def _side_effect(*args, **kwargs):
        raise ValueError("sid is required to fetch job/results from Splunk REST")

    with patch("api.routes.ingest.enrich_alert_from_splunk", new_callable=AsyncMock) as m:
        m.side_effect = _side_effect
        yield m


@pytest.fixture
def mock_enrich_generic_error() -> Generator[AsyncMock, None, None]:
    async def _side_effect(*args, **kwargs):
        raise RuntimeError("connection refused")

    with patch("api.routes.ingest.enrich_alert_from_splunk", new_callable=AsyncMock) as m:
        m.side_effect = _side_effect
        yield m
