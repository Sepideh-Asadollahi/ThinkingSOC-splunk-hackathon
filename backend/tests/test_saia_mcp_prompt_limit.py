"""SAIA MCP saia_generate_spl prompt must be <= 1000 chars."""

from __future__ import annotations

from splunk.mcp.spl_assistant import build_saia_generate_args, _SAIA_MCP_PROMPT_MAX


def test_saia_prompt_under_mcp_limit(test_settings) -> None:
    normalized = {
        "host": "we8105desk",
        "user": "SYSTEM",
        "Image": "C:\\Windows\\System32\\osk.exe",
        "ParentCommandLine": "powershell.exe -File C:\\Users\\Public\\invoke.ps1",
        "orig_search": "index=botsv1 " + ("x" * 500),
    }
    objective = (
        "What is the exact content (hash, size, and code) of the script "
        "C:\\Users\\Public\\invoke.ps1 on we8105desk?"
    )
    args = build_saia_generate_args(
        test_settings,
        normalized=normalized,
        search_name="Suspicious Process - osk.exe Sysmon EID 1 (botsv1)",
        objective=objective,
        datamodel="Endpoint",
    )
    prompt = args["prompt"]
    assert len(prompt) <= _SAIA_MCP_PROMPT_MAX
    assert "Question:" in prompt
    assert args.get("spl_only") is False
    assert "additional_context" in args
    assert "Alert fields JSON" in args["additional_context"]
    assert len(args["additional_context"]) > len(prompt)
