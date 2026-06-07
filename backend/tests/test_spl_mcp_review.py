"""SPL: LiteLLM generation + review pipeline."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from config import Settings
from models.analysis import RootCauseSpl
from services.splunk_integration.splunk_ai_assistant import suggest_spl_for_alert


@pytest.mark.asyncio
async def test_suggest_spl_llm_when_enabled():
    settings = Settings(
        tsoc_spl_llm_review=True,
        tsoc_spl_use_rest_predict=False,
        tsoc_execute_investigation_spl=False,
    )
    llm_rc_spl = {
        "spl": 'search index=main user="jdoe" | stats count',
        "explanation": "Failed logins for user.",
        "time_window": "earliest=-24h@h latest=now",
        "pivots": ["user"],
        "notes": ["llm_generated_spl"],
    }

    with (
        patch(
            "services.investigation.investigation_questions_spl.generate_investigation_spl_via_llm",
            new_callable=AsyncMock,
            return_value=RootCauseSpl(**llm_rc_spl),
        ),
        patch(
            "services.splunk_integration.splunk_ai_assistant.validate_root_cause_spl",
            new_callable=AsyncMock,
        ) as validate_mock,
    ):
        from models.analysis import RootCauseSplValidation

        validate_mock.return_value = RootCauseSplValidation(method="skipped", valid=True)
        rc, source = await suggest_spl_for_alert(
            settings,
            normalized={"host": "web-prod-01", "user": "jdoe"},
            search_name="failed login",
            sid=None,
            splunk_results=[],
            objective="find root cause",
        )

    assert source == "llm"
    assert "search index=main" in rc.spl


@pytest.mark.asyncio
async def test_suggest_spl_rule_based_when_llm_unavailable():
    settings = Settings(
        tsoc_spl_use_rest_predict=False,
        tsoc_execute_investigation_spl=False,
        litellm_api_key=None,
    )
    with patch(
        "services.splunk_integration.splunk_ai_assistant._generate_spl_via_llm",
        new_callable=AsyncMock,
        return_value=None,
    ):
        rc, source = await suggest_spl_for_alert(
            settings,
            normalized={"host": "web-prod-01", "user": "jdoe", "index": "main"},
            search_name="failed login",
            sid=None,
            splunk_results=[],
            objective="find root cause",
        )
    assert source == "rule_based"
    assert rc.spl.lower().startswith("search")
