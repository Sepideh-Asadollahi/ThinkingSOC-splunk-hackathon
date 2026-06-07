"""Splunk 10+ search/v2/parser uses POST (GET on v1 parser returns method not allowed)."""

from __future__ import annotations

from splunk.client.rest_client import SplunkRestClient


def test_spl_query_for_parser_prefixes_tstats() -> None:
    q = SplunkRestClient._spl_query_for_parser(
        "| tstats count from datamodel=Authentication where nodename=Authentication.*"
    )
    assert q.lower().startswith("| tstats")


def test_parse_spl_v2_path_in_source() -> None:
    import inspect

    src = inspect.getsource(SplunkRestClient.parse_spl)
    assert "search/v2/parser" in src
    assert "client.post" in src
    assert "client.get" not in src
