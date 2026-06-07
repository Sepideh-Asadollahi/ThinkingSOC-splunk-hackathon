"""LLM prepares SAIA prompt before MCP generate."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from services.investigation.saia_prompt_prepare import prepare_saia_prompt_with_llm
from splunk.mcp.spl_assistant import build_saia_generate_args, _SAIA_MCP_PROMPT_MAX


@pytest.mark.asyncio
async def test_prepare_returns_prompt_under_limit(test_settings) -> None:
    settings = test_settings.model_copy(
        update={"tsoc_saia_llm_prepare_prompt": True}
    )
    long_q = "Investigate script " + ("x" * 500)
    with patch(
        "services.investigation.saia_prompt_prepare.llm_json_response",
        new_callable=AsyncMock,
        return_value={
            "saia_prompt": "Alert: osk. Question: find invoke.ps1 on host. Use | tstats only.",
            "rationale": "focused",
        },
    ):
        prompt, ok = await prepare_saia_prompt_with_llm(
            settings,
            normalized={"host": "we8105desk", "Image": "osk.exe"},
            search_name="osk alert",
            objective=long_q,
            datamodel="Endpoint",
        )
    assert ok is True
    assert prompt is not None
    assert len(prompt) <= _SAIA_MCP_PROMPT_MAX


@pytest.mark.asyncio
async def test_generate_spl_uses_prepared_prompt_in_args(test_settings) -> None:
    settings = test_settings.model_copy(
        update={"tsoc_saia_llm_prepare_prompt": True}
    )
    prepared = "Short SAIA question under limit."
    args = build_saia_generate_args(
        settings,
        normalized={"host": "h1"},
        search_name="alert",
        objective="full objective here",
        saia_prompt=prepared,
    )
    assert args["prompt"] == prepared
    assert "additional_context" in args
