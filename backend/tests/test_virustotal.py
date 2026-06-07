"""Unit tests for VirusTotal IOC extraction, client, and enrichment."""

from __future__ import annotations

import base64
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from config import Settings
from services.threat_intel.virustotal import (
    VirusTotalClient,
    domain_vt_skip_reason,
    _host_from_url,
    _maybe_domain,
    _url_id_base64,
    enrich_virustotal,
    extract_iocs,
    is_public_ip,
)
from tests.fixtures.virustotal_api import (
    vt_domain_response,
    vt_file_response,
    vt_ip_response,
    vt_url_response,
)


class TestIsPublicIp:
    def test_public_ipv4(self) -> None:
        assert is_public_ip("8.8.8.8") is True
        assert is_public_ip("1.1.1.1") is True

    def test_private_and_special(self) -> None:
        assert is_public_ip("10.0.0.1") is False
        assert is_public_ip("192.168.1.1") is False
        assert is_public_ip("127.0.0.1") is False
        assert is_public_ip("169.254.0.1") is False

    def test_invalid(self) -> None:
        assert is_public_ip("") is False
        assert is_public_ip("not-an-ip") is False


class TestUrlHelpers:
    def test_url_id_base64_matches_vt_spec(self) -> None:
        url = "http://www.cztapwlwk.net/plafgxc80333067532"
        expected = base64.urlsafe_b64encode(url.encode("utf-8")).decode("utf-8").rstrip("=")
        assert _url_id_base64(url) == expected

    def test_host_from_url(self) -> None:
        assert _host_from_url("https://evil.example/a") == "evil.example"
        assert _host_from_url("not-a-url") is None

    def test_maybe_domain(self) -> None:
        assert _maybe_domain("web-prod-01.corp.local") == "web-prod-01.corp.local"
        assert _maybe_domain("8.8.8.8") is None
        assert _maybe_domain("bad host name") is None


class TestExtractIocs:
    def test_empty_when_max_zero(self) -> None:
        out = extract_iocs({"ip": "8.8.8.8"}, [], max_iocs=0)
        assert out == {"file_hashes": [], "ips": [], "domains": [], "urls": []}

    def test_priority_hash_before_ip_when_trimmed(self) -> None:
        md5 = "44d88612fea8a8f36de82e1278abb02f"
        out = extract_iocs(
            {"hash": md5, "dest_ip": "8.8.8.8"},
            [],
            max_iocs=1,
        )
        assert out["file_hashes"] == [md5]
        assert out["ips"] == []

    def test_src_dest_hostname_not_domain_only_public_ip(self) -> None:
        out = extract_iocs({"src": "cdn.example.com", "dest": "10.0.0.5"}, [], max_iocs=8)
        assert "cdn.example.com" not in out["domains"]
        assert out["domains"] == []
        assert "10.0.0.5" not in out["ips"]

    def test_src_dest_public_ip(self) -> None:
        out = extract_iocs({"src": "8.8.8.8", "dest": "1.1.1.1"}, [], max_iocs=8)
        assert "8.8.8.8" in out["ips"]
        assert "1.1.1.1" in out["ips"]

    def test_host_computer_not_used_for_domain(self) -> None:
        out = extract_iocs(
            {"host": "we8105desk", "Computer": "we8105desk", "domain": "pastebin.com"},
            [],
            max_iocs=8,
        )
        assert out["domains"] == ["pastebin.com"]

    def test_internal_domain_skipped_at_extraction(self) -> None:
        out = extract_iocs(
            {"fqdn": "we8105desk.botsv1.local", "domain": "dc-01.corp.local"},
            [],
            max_iocs=8,
        )
        assert out["domains"] == []

    def test_regex_only_on_vt_scoped_fields(self) -> None:
        sha = "a" * 64
        out = extract_iocs(
            {"CommandLine": "curl https://evil.example " + sha},
            [{"_raw": "connect https://evil.example/path sha256=" + sha}],
            max_iocs=8,
        )
        assert out["file_hashes"] == []
        assert out["urls"] == []
        assert out["ips"] == []

    def test_regex_on_hash_field_value(self) -> None:
        sha = "a" * 64
        out = extract_iocs({"hash": "prefix " + sha + " suffix"}, [], max_iocs=8)
        assert sha in out["file_hashes"]

    def test_url_yields_domain_from_host(self) -> None:
        out = extract_iocs(
            {"url": "https://pastebin.com/raw/abc"},
            [],
            max_iocs=8,
        )
        assert out["urls"]
        assert "pastebin.com" in out["domains"]


class TestDomainVtSkip:
    def test_example_tld_skipped(self) -> None:
        reason = domain_vt_skip_reason("dc-01.corp.example")
        assert reason is not None
        assert ".example" in reason

    def test_short_hostname_skipped(self) -> None:
        reason = domain_vt_skip_reason("dc-01")
        assert reason is not None
        assert "FQDN" in reason

    def test_internal_local_skipped(self) -> None:
        reason = domain_vt_skip_reason("we8105desk.botsv1.local")
        assert reason is not None
        assert ".local" in reason


class TestVirusTotalClient:
    def test_configured_requires_key(self, test_settings: Settings) -> None:
        s = test_settings.model_copy(update={"virustotal_api_key": ""})
        assert VirusTotalClient(s).configured() is False
        s2 = test_settings.model_copy(update={"virustotal_api_key": "test-key"})
        assert VirusTotalClient(s2).configured() is True

    @pytest.mark.asyncio
    async def test_get_json_404(self, test_settings: Settings) -> None:
        s = test_settings.model_copy(update={"virustotal_api_key": "k"})
        client = VirusTotalClient(s)
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.raise_for_status = MagicMock()

        mock_http = AsyncMock()
        mock_http.get = AsyncMock(return_value=mock_resp)
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_http)
        mock_cm.__aexit__ = AsyncMock(return_value=None)

        with patch("services.threat_intel.virustotal.httpx.AsyncClient", return_value=mock_cm):
            data, err = await client.ip_report("203.0.113.9")
        assert data is None
        assert err == "not_found"

    @pytest.mark.asyncio
    async def test_domain_report_skips_example_without_http(self, test_settings: Settings) -> None:
        s = test_settings.model_copy(update={"virustotal_api_key": "k"})
        client = VirusTotalClient(s)
        with patch("services.threat_intel.virustotal.httpx.AsyncClient") as mock_client_cls:
            data, err = await client.domain_report("dc-01.corp.example")
        mock_client_cls.assert_not_called()
        assert data is None
        assert err is not None
        assert err.startswith("skipped:")
        assert ".example" in err

    @pytest.mark.asyncio
    async def test_get_json_400_logs_detail(self, test_settings: Settings, caplog) -> None:
        import logging

        caplog.set_level(logging.WARNING)
        s = test_settings.model_copy(update={"virustotal_api_key": "k"})
        client = VirusTotalClient(s)
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.json = MagicMock(
            return_value={"error": {"code": "InvalidArgumentError", "message": "Invalid domain"}}
        )
        mock_resp.text = '{"error":{"message":"Invalid domain"}}'

        mock_http = AsyncMock()
        mock_http.get = AsyncMock(return_value=mock_resp)
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_http)
        mock_cm.__aexit__ = AsyncMock(return_value=None)

        with patch("services.threat_intel.virustotal.httpx.AsyncClient", return_value=mock_cm):
            data, err = await client.domain_report("bad..domain")
        assert data is None
        assert err is not None
        assert "http_400" in err
        assert any("virustotal domain lookup failed" in r.message for r in caplog.records)
        assert any("Invalid domain" in r.message for r in caplog.records)

    @pytest.mark.asyncio
    async def test_get_json_success(self, test_settings: Settings) -> None:
        s = test_settings.model_copy(update={"virustotal_api_key": "k"})
        client = VirusTotalClient(s)
        payload = vt_ip_response("1.1.1.1")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json = MagicMock(return_value=payload)
        mock_resp.raise_for_status = MagicMock()

        mock_http = AsyncMock()
        mock_http.get = AsyncMock(return_value=mock_resp)
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_http)
        mock_cm.__aexit__ = AsyncMock(return_value=None)

        with patch("services.threat_intel.virustotal.httpx.AsyncClient", return_value=mock_cm):
            data, err = await client.ip_report("1.1.1.1")
        assert err is None
        assert data["data"]["type"] == "ip_address"


@pytest.mark.asyncio
async def test_enrich_disabled(test_settings: Settings) -> None:
    s = test_settings.model_copy(update={"virustotal_enable": False})
    out = await enrich_virustotal(s, normalized={"ip": "8.8.8.8"}, splunk_results_preview=[])
    assert out["enabled"] is False


@pytest.mark.asyncio
async def test_enrich_no_api_key(test_settings: Settings) -> None:
    s = test_settings.model_copy(update={"virustotal_enable": True, "virustotal_api_key": None})
    out = await enrich_virustotal(s, normalized={"ip": "8.8.8.8"}, splunk_results_preview=[])
    assert out["enabled"] is False
    assert out.get("reason") == "no_api_key"


@pytest.mark.asyncio
async def test_enrich_queries_each_ioc_type(test_settings: Settings) -> None:
    md5 = "44d88612fea8a8f36de82e1278abb02f"
    sha256 = "a" * 64
    s = test_settings.model_copy(
        update={
            "virustotal_enable": True,
            "virustotal_api_key": "test-key",
            "virustotal_max_iocs": 8,
        }
    )

    async def fake_get_json(path: str, **kwargs):
        if path.startswith("/files/"):
            return vt_file_response(sha256), None
        if path.startswith("/ip_addresses/"):
            return vt_ip_response("1.1.1.1"), None
        if path.startswith("/domains/"):
            return vt_domain_response("pastebin.com"), None
        if path.startswith("/urls/"):
            return vt_url_response(), None
        return None, "not_found"

    with patch.object(VirusTotalClient, "_get_json", side_effect=fake_get_json):
        out = await enrich_virustotal(
            s,
            normalized={
                "hash": md5,
                "ip": "1.1.1.1",
                "domain": "pastebin.com",
                "url": "http://pastebin.com/x",
            },
            splunk_results_preview=[],
        )

    assert out["enabled"] is True
    assert md5 in out["files"]
    assert out["files"][md5]["summary"]["type"] == "file"
    assert "1.1.1.1" in out["ips"]
    assert out["ips"]["1.1.1.1"]["summary"]["last_analysis_stats"]["malicious"] == 12
    assert "pastebin.com" in out["domains"]
    assert out["domains"]["pastebin.com"]["summary"]["categories"]["Dr.Web"] == "malware"
    assert out["urls"]
    url_key = next(iter(out["urls"]))
    assert out["urls"][url_key]["summary"]["type"] == "url"
