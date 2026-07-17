"""SAIA MCP response parsing — multi-line SPL extraction."""

from __future__ import annotations

from splunk.mcp.saia.parse import parse_explain_text
from splunk.mcp.spl_assistant import _extract_spl_from_saia_text, _parse_saia_spl_result


def test_extract_multiline_datamodel_spl_from_log_shape() -> None:
    raw = """splunk-spl
| datamodel Endpoint Processes search
    processes.parent_process_image="C:\\\\Windows\\\\System32\\\\WindowsPowerShell\\\\v1.0\\\\powershell.exe"
    processes.dest="we8105desk"
| where _time>=strptime("2018-08-20T21:04:41-07:00","%Y-%m-%dT%H:%M:%S%z")
    AND _time<=strptime("2018-08-20T21:14:41-07:00","%Y-%m-%dT%H:%M:%S%z")
| rename processes.image as Image, processes.commandline as CommandLine, processes.process_hash as Hash
| table Image CommandLine Hash
"""
    spl = _extract_spl_from_saia_text(raw)
    assert "datamodel Endpoint Processes search" in spl
    assert "processes.parent_process_image" in spl
    assert "processes.dest=\"we8105desk\"" in spl
    assert "| where _time>=" in spl
    assert "| table Image CommandLine Hash" in spl
    assert spl != "| datamodel Endpoint Processes search"


def test_parse_saia_mcp_results_wrapper() -> None:
    payload = {
        "results": [
            {
                "response": [
                    "splunk-spl\n| datamodel Endpoint Processes search *\n| stats count"
                ]
            }
        ]
    }
    spl, expl = _parse_saia_spl_result(payload)
    assert "datamodel Endpoint Processes search *" in spl
    assert "| stats count" in spl
    assert expl == ""


def test_extract_multiline_spl_with_eventstats_from_log_shape() -> None:
    """Regression: SAIA osk.exe hunt returns eventstats/where/table after eval."""
    raw = """splunk-spl
| datamodel Endpoint Processes search
| eval is_osk=if(host="we8105desk" AND Image="C:\\\\Windows\\\\System32\\\\osk.exe" AND like(ParentImage,"%powershell.exe%"),1,0)
| eventstats values(ParentProcessId) as target_ppid values(_time) as target_time by host
| where is_osk=0
      AND host="we8105desk"
      AND parent_process_id=target_ppid
      AND _time>=relative_time(target_time,"-5m")
      AND _time<=relative_time(target_time,"+5m")
| table Image CommandLine
"""
    spl = _extract_spl_from_saia_text(raw)
    assert "| eventstats values(ParentProcessId)" in spl
    assert "| where is_osk=0" in spl
    assert "| table Image CommandLine" in spl
    assert spl.count("| eval is_osk=") == 1


def test_parse_spl_only_list_with_splunk_spl_prefix_line() -> None:
    raw = {
        "results": [
            {
                "response": [
                    "Endpoint",
                    "splunk-spl",
                    "tstats summariesonly=t values(CommandLine) FROM datamodel=Endpoint.Process "
                    'WHERE index=botsv1 User="bob" BY Computer,User',
                ]
            }
        ]
    }
    spl, _ = _parse_saia_spl_result(raw)
    assert spl.startswith("| tstats")
    assert "summariesonly=t" in spl
    assert "splunk-spl" not in spl


def test_parse_markdown_reasoning_and_spl_block() -> None:
    raw = {
        "results": [
            {
                "response": (
                    "**Summary of reasoning**\n\n1. Use Endpoint datamodel.\n\n"
                    "**Generated SPL**\n\n```splunk-spl\n"
                    "| tstats summariesonly=t values(Process.command_line) "
                    "FROM datamodel=Endpoint WHERE index=botsv1\n"
                    "| table Computer\n```"
                )
            }
        ]
    }
    spl, expl = _parse_saia_spl_result(raw)
    assert "tstats summariesonly=t" in spl
    assert "Process.command_line" in spl
    assert "Summary of reasoning" in expl
    assert "| table Computer" in spl


def test_parse_unclosed_markdown_fence_keeps_index_base_search() -> None:
    """Regression: streamed SAIA responses may omit the closing code fence."""
    raw = {
        "results": [
            {
                "response": (
                    "**Reasoning**\nUse audit data.\n\n**SPL**\n\n"
                    "```splunk-spl\n"
                    "index=audit_summary sourcetype=stash user=admin result=failure\n"
                    "| timechart span=1d count as failed_logins by host\n"
                    "| sort _time\n"
                )
            }
        ]
    }
    spl, expl = _parse_saia_spl_result(raw)
    assert spl.startswith("index=audit_summary")
    assert "sourcetype=stash" in spl
    assert "| timechart span=1d" in spl
    assert "| sort _time" in spl
    assert "Reasoning" in expl


def test_parse_explain_text_from_mcp_results_wrapper() -> None:
    raw = {
        "results": [
            {
                "response": (
                    "**1. Data source**  \n- Index: `main`\n\n"
                    "**6. Author's intent**  \nCount admin events.\n\n"
                    "```splunk-spl\nsearch index=main user=\"admin\" | stats count\n```"
                )
            }
        ]
    }
    text = parse_explain_text(raw)
    assert "Data source" in text
    assert "Author's intent" in text
    assert "search index=main" not in text


def test_parse_saia_prose_response_is_not_treated_as_spl() -> None:
    prose = (
        "This SPL cannot be improved by any SPL Optimization rules known by SAIA. "
        "Consider executing the search over a shorter time range."
    )
    spl, _ = _parse_saia_spl_result({"results": [{"response": [prose]}]})
    assert "|" not in spl
    assert "datamodel" not in spl.lower()
