"""SplunkRestClient tests with httpx.MockTransport (no real Splunk)."""

from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest

from config import Settings
from splunk.client import SplunkRestClient, _parse_session_key
from splunk.client.oneshot_json import parse_oneshot_json


def test_parse_session_key_extracts_key() -> None:
    xml = "<response><sessionKey>abc-session</sessionKey></response>"
    assert _parse_session_key(xml) == "abc-session"


def test_parse_session_key_missing_raises() -> None:
    with pytest.raises(ValueError, match="sessionKey"):
        _parse_session_key("<response></response>")


def _make_transport_v2() -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if request.method == "POST" and "services/auth/login" in url:
            return httpx.Response(
                200,
                text="<response><sessionKey>SK_TEST</sessionKey></response>",
            )
        if request.method == "GET" and "/services/search/jobs/job_sid_1" in url and "results" not in url:
            return httpx.Response(200, json={"entry": [{"name": "job_sid_1"}]})
        if request.method == "GET" and "/services/search/v2/jobs/job_sid_1/results" in url:
            return httpx.Response(
                200,
                json={"results": [{"_raw": "line1"}, {"_raw": "line2"}], "init_offset": 0},
            )
        return httpx.Response(404, text="unexpected: " + url)

    return httpx.MockTransport(handler)


@pytest.fixture
def settings_v2() -> Settings:
    return Settings(
        splunk_mgmt_url="https://127.0.0.1:8089",
        splunk_username="u",
        splunk_password="p",
        splunk_verify_ssl=False,
    )


@pytest.mark.asyncio
async def test_login_get_job_fetch_results_v2(settings_v2: Settings) -> None:
    transport = _make_transport_v2()

    def fake_client(_self: SplunkRestClient) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            transport=transport,
            base_url="https://127.0.0.1:8089",
            verify=False,
            timeout=30.0,
        )

    client = SplunkRestClient(settings_v2)
    with patch.object(SplunkRestClient, "_client", fake_client):
        sk = await client.login()
        assert sk == "SK_TEST"
        job = await client.get_job("job_sid_1", sk)
        assert "entry" in job
        rows = await client.fetch_all_results("job_sid_1", sk)
        assert len(rows) == 2
        assert rows[0]["_raw"] == "line1"


@pytest.mark.asyncio
async def test_login_requires_credentials(settings_v2: Settings) -> None:
    s = Settings(
        splunk_mgmt_url="https://127.0.0.1:8089",
        splunk_username="",
        splunk_password="",
        splunk_verify_ssl=False,
    )
    client = SplunkRestClient(s)
    with pytest.raises(ValueError, match="splunk_username"):
        await client.login()


def test_parse_oneshot_json_fatal_message() -> None:
    with pytest.raises(RuntimeError, match="Splunk search error"):
        parse_oneshot_json({"messages": [{"type": "FATAL", "text": "bad SPL"}]})

