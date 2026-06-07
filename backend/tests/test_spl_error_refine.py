"""SPL parser errors are passed to LiteLLM for correction."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from config import Settings
from models.analysis import RootCauseSpl, RootCauseSplValidation
from services.investigation.spl_mcp_review import (
    refine_root_cause_spl_until_valid,
    refine_spl_with_llm_on_error,
    spl_validation_is_error,
)


def test_spl_validation_is_error() -> None:
    assert spl_validation_is_error(
        RootCauseSplValidation(method="splunk_parser", valid=False, message="syntax error")
    )
    assert not spl_validation_is_error(
        RootCauseSplValidation(method="splunk_parser", valid=True, message=None)
    )
    assert not spl_validation_is_error(
        RootCauseSplValidation(method="skipped", valid=None, message="no creds")
    )


@pytest.mark.asyncio
async def test_refine_spl_with_llm_includes_error_message(test_settings: Settings) -> None:
    settings = test_settings.model_copy(
        update={"tsoc_spl_llm_refine_on_error": True}
    )
    draft = RootCauseSpl(
        spl='search index=main | stats bad_field',
        validation=RootCauseSplValidation(
            method="splunk_parser", valid=False, message="Error in 'stats' command"
        ),
    )
    fixed = RootCauseSpl(
        spl='search index=main | stats count by user',
        notes=["llm_refine_after_parser_error_1"],
    )

    with patch(
        "services.investigation.spl_mcp_review.llm_json_response",
        new_callable=AsyncMock,
        return_value={
            "spl": fixed.spl,
            "explanation": "fixed",
            "notes": fixed.notes,
        },
    ) as mock_llm:
        out, ok = await refine_spl_with_llm_on_error(
            settings,
            draft=draft,
            error_message="Error in 'stats' command",
            error_source="splunk_parser",
            normalized={"user": "alice"},
            search_name="alert",
            sid=None,
            splunk_results=[],
            objective="failed logins?",
        )

    assert ok is True
    assert out.spl == fixed.spl
    user_msg = mock_llm.await_args[0][2]
    assert "Error in 'stats' command" in user_msg
    assert "Splunk error (must fix)" in user_msg


@pytest.mark.asyncio
async def test_refine_until_valid_revalidates(test_settings: Settings) -> None:
    settings = test_settings.model_copy(
        update={
            "tsoc_spl_llm_refine_on_error": True,
            "tsoc_spl_execute_refine_max_attempts": 2,
        }
    )
    rc = RootCauseSpl(
        spl="search index=main bad",
        validation=RootCauseSplValidation(
            method="splunk_parser", valid=False, message="bad syntax"
        ),
    )
    fixed_spl = "search index=main | stats count"
    validations = [
        RootCauseSplValidation(method="splunk_parser", valid=False, message="bad syntax"),
        RootCauseSplValidation(method="splunk_parser", valid=True, message=None),
    ]

    with (
        patch(
            "services.investigation.spl_mcp_review.llm_json_response",
            new_callable=AsyncMock,
            return_value={"spl": fixed_spl, "explanation": "ok", "notes": []},
        ),
        patch(
            "services.soc_analysis.soc_analysis_root_cause_spl.validate_root_cause_spl",
            new_callable=AsyncMock,
            side_effect=lambda _s, r, **_: validations.pop(0),
        ),
    ):
        out, any_fixed = await refine_root_cause_spl_until_valid(
            settings,
            rc,
            normalized={},
            objective="test",
        )

    assert any_fixed is True
    assert out.spl == fixed_spl
    assert out.validation is not None
    assert out.validation.valid is True
