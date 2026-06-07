"""Investigation SPL: LiteLLM when enabled, rule-based search fallback."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from config import Settings
from models.analysis import InvestigationQuestionItem, RootCauseSpl
from services.investigation.investigation_questions_spl import fill_investigation_spl


@pytest.mark.asyncio
async def test_fill_investigation_llm_source(test_settings: Settings) -> None:
    settings = test_settings.model_copy(
        update={"tsoc_analysis_saia_spl_review": False}
    )
    items = [InvestigationQuestionItem(question="Failed logins?", spl="")]
    llm_rc = RootCauseSpl(
        spl='search index=main user="admin" | stats count',
        explanation="from llm",
        notes=["llm_generated_spl"],
    )

    with (
        patch(
            "services.investigation.investigation_questions_spl.generate_investigation_spl_via_llm",
            new_callable=AsyncMock,
            return_value=llm_rc,
        ) as mock_llm_gen,
        patch(
            "services.investigation.investigation_questions_spl.validate_root_cause_spl",
            new_callable=AsyncMock,
            return_value=None,
        ),
    ):
        out, source = await fill_investigation_spl(
            settings,
            items,
            {"user": "admin"},
            search_name="auth alert",
            canonical_prefix='{"alert":{}}',
        )

    assert source == "llm"
    mock_llm_gen.assert_awaited_once()
    assert "search index=main" in out[0].spl


@pytest.mark.asyncio
async def test_fill_investigation_rule_based_when_llm_disabled(test_settings: Settings) -> None:
    settings = test_settings.model_copy(
        update={"tsoc_analysis_saia_spl_review": False}
    )
    items = [InvestigationQuestionItem(question="Q?", spl="")]

    out, source = await fill_investigation_spl(settings, items, {"index": "botsv1", "user": "admin"})

    assert source == "rule_based"
    assert out[0].spl.lower().startswith("search")
