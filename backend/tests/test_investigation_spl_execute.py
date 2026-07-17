from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from config import Settings
from models.analysis import SplSearchResult
from services.investigation.investigation_spl_execute import _readable_rows, _run_one


def test_readable_rows_truncates_long_lists() -> None:
    rows = [
        {
            "dest_ips": [str(i) for i in range(40)],
            "count": "40",
        }
    ]
    out = _readable_rows(rows)
    vals = out[0]["dest_ips"]
    assert isinstance(vals, list)
    assert len(vals) == 26
    assert vals[-1] == "... (+15 more)"


def test_readable_rows_truncates_long_strings() -> None:
    rows = [{"blob": "x" * 500}]
    out = _readable_rows(rows)
    blob = out[0]["blob"]
    assert isinstance(blob, str)
    assert blob.endswith("... (+180 chars)")


def _settings() -> Settings:
    return Settings(
        splunk_mgmt_url="https://splunk.test:8089",
        splunk_username="svc",
        splunk_password="secret",
        splunk_verify_ssl=False,
        tsoc_mcp_enabled=True,
        splunk_mcp_url="https://splunk.test:8089/services/mcp",
        splunk_mcp_token="token",
        tsoc_spl_execute_via_mcp=True,
    )


@pytest.mark.asyncio
async def test_mcp_failure_falls_back_to_splunk_rest_api() -> None:
    client = MagicMock()
    client.oneshot_search = AsyncMock(return_value=[{"user": "alice"}])
    with (
        patch(
            "services.investigation.investigation_spl_execute.mcp_configured",
            return_value=True,
        ),
        patch(
            "services.investigation.investigation_spl_execute.execute_spl_via_mcp",
            new_callable=AsyncMock,
            return_value=SplSearchResult(error="MCP endpoint unavailable"),
        ) as execute_mcp,
    ):
        result = await _run_one(
            _settings(), client, "session-key", "search index=auth", app="search"
        )

    execute_mcp.assert_awaited_once()
    client.oneshot_search.assert_awaited_once()
    assert result.error is None
    assert result.execution_transport == "rest"
    assert result.rows == [{"user": "alice"}]


@pytest.mark.asyncio
async def test_mcp_not_configured_uses_splunk_rest_api_directly() -> None:
    client = MagicMock()
    client.oneshot_search = AsyncMock(return_value=[{"count": "1"}])
    with (
        patch(
            "services.investigation.investigation_spl_execute.mcp_configured",
            return_value=False,
        ),
        patch(
            "services.investigation.investigation_spl_execute.execute_spl_via_mcp",
            new_callable=AsyncMock,
        ) as execute_mcp,
    ):
        result = await _run_one(
            _settings(), client, "session-key", "search index=auth", app="search"
        )

    execute_mcp.assert_not_awaited()
    client.oneshot_search.assert_awaited_once()
    assert result.execution_transport == "rest"


@pytest.mark.asyncio
async def test_successful_mcp_does_not_duplicate_query_through_rest() -> None:
    client = MagicMock()
    client.oneshot_search = AsyncMock()
    with (
        patch(
            "services.investigation.investigation_spl_execute.mcp_configured",
            return_value=True,
        ),
        patch(
            "services.investigation.investigation_spl_execute.execute_spl_via_mcp",
            new_callable=AsyncMock,
            return_value=SplSearchResult(row_count=1, rows=[{"count": "1"}]),
        ),
    ):
        result = await _run_one(
            _settings(), client, "session-key", "search index=auth", app="search"
        )

    client.oneshot_search.assert_not_awaited()
    assert result.execution_transport == "mcp"


@pytest.mark.asyncio
async def test_both_transport_errors_are_preserved() -> None:
    client = MagicMock()
    client.oneshot_search = AsyncMock(side_effect=RuntimeError("REST login expired"))
    with (
        patch(
            "services.investigation.investigation_spl_execute.mcp_configured",
            return_value=True,
        ),
        patch(
            "services.investigation.investigation_spl_execute.execute_spl_via_mcp",
            new_callable=AsyncMock,
            return_value=SplSearchResult(error="MCP timeout"),
        ),
    ):
        result = await _run_one(
            _settings(), client, "session-key", "search index=auth", app="search"
        )

    assert "MCP timeout" in str(result.error)
    assert "REST login expired" in str(result.error)
