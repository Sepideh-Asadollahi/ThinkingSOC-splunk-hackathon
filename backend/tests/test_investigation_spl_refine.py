"""Execute + refine loop (LiteLLM after 0 rows / errors)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from config import Settings
from models.analysis import (
    InvestigationQuestionItem,
    RootCauseSpl,
    RootCauseSplValidation,
    SplSaiaAnalysis,
    SplSearchResult,
)
from services.investigation.investigation_questions_spl import (
    run_investigation_item_execute_refine_loop,
    validate_investigation_question_items,
)
from services.investigation.investigation_spl_execute import needs_spl_execution_refine


def test_needs_spl_execution_refine() -> None:
    assert needs_spl_execution_refine(SplSearchResult(row_count=0, rows=[])) is True
    assert needs_spl_execution_refine(SplSearchResult(row_count=0, rows=[], error="bad")) is True
    assert needs_spl_execution_refine(SplSearchResult(row_count=2, rows=[{"a": "1"}])) is False
    assert needs_spl_execution_refine(None) is False


@pytest.mark.asyncio
async def test_validation_auto_repairs_missing_eval_boolean_operator(
    test_settings: Settings,
) -> None:
    item = InvestigationQuestionItem(
        question="Is the signature valid?",
        spl=(
            'search index=firewall | eval is_benign=if(isnotnull(Sub_Status) '
            '(Sub_Status="Valid" OR Sub_Status="Trusted"),1,0) | table is_benign'
        ),
    )
    valid = RootCauseSplValidation(
        method="splunk_parser",
        valid=True,
        message="OK",
    )

    with patch(
        "services.investigation.investigation_questions_spl.validate_root_cause_spl",
        new_callable=AsyncMock,
        return_value=valid,
    ) as validate:
        out = await validate_investigation_question_items(
            test_settings,
            [item],
            refine_on_error=False,
        )

    checked = validate.await_args.args[1]
    assert "isnotnull(Sub_Status) AND (" in checked.spl
    assert "isnotnull(Sub_Status) AND (" in out[0].spl
    assert "auto_repaired_spl_syntax" in out[0].notes


@pytest.mark.asyncio
async def test_validation_rejects_invalid_saia_optimization_and_uses_valid_input(
    test_settings: Settings,
) -> None:
    original = 'search index=identity user="alice" | stats count by user'
    optimized = (
        'search index=identity | stats '
        'dc(eval(if(is_success,src,null()))) as successful_src_count by user'
    )
    item = InvestigationQuestionItem(
        question="Compare successful sources",
        spl=optimized,
        spl_saia_analysis=SplSaiaAnalysis(
            optimized=True,
            spl_before_optimize=original,
            steps=["optimize", "explain"],
        ),
    )
    invalid = RootCauseSplValidation(
        method="splunk_parser",
        valid=False,
        message="invalid eval expression",
    )
    valid = RootCauseSplValidation(
        method="splunk_parser",
        valid=True,
        message="OK",
    )

    with patch(
        "services.investigation.investigation_questions_spl.validate_root_cause_spl",
        new_callable=AsyncMock,
        side_effect=[invalid, valid],
    ) as validate:
        out = await validate_investigation_question_items(
            test_settings,
            [item],
            refine_on_error=False,
        )

    assert validate.await_count == 2
    assert out[0].spl == original
    assert out[0].validation is not None and out[0].validation.valid is True
    assert "saia_optimization_rejected_parser_fallback" in out[0].notes


@pytest.mark.asyncio
async def test_refine_loop_stops_after_max_attempts(test_settings: Settings) -> None:
    settings = test_settings.model_copy(
        update={
            "tsoc_spl_execute_refine_max_attempts": 2,
            "tsoc_execute_investigation_spl": True,
            "splunk_username": "admin",
            "splunk_password": "x",
        }
    )
    item = InvestigationQuestionItem(
        question="Any failed logins?",
        spl='search index=main user="alice" | stats count',
        notes=["llm_generated_spl"],
    )
    zero = SplSearchResult(row_count=0, rows=[])
    llm_rc = RootCauseSpl(
        spl='search index=main user="alice" | stats count by src',
        notes=["llm_refine_after_execute_1"],
    )

    client = MagicMock()
    with (
        patch(
            "services.investigation.investigation_questions_spl.validate_investigation_question_items",
            new_callable=AsyncMock,
            side_effect=lambda _s, items, **_: items,
        ),
        patch(
            "services.investigation.investigation_questions_spl.execute_investigation_item",
            new_callable=AsyncMock,
            return_value=item.model_copy(update={"spl_results": zero}),
        ),
        patch(
            "services.investigation.investigation_questions_spl.review_spl_after_execution_with_llm",
            new_callable=AsyncMock,
            return_value=(llm_rc, True),
        ) as mock_llm_refine,
        patch(
            "services.investigation.investigation_questions_spl.analyze_spl_execution_results_with_llm",
            new_callable=AsyncMock,
            return_value={"summary": "no rows", "usefulness": "low"},
        ) as mock_result_analysis,
    ):
        out = await run_investigation_item_execute_refine_loop(
            settings,
            item,
            normalized={"user": "alice"},
            search_name="test",
            sid="sid1",
            splunk_results=[],
            client=client,
            session_key="sk",
        )

    assert mock_llm_refine.await_count == 2
    assert mock_result_analysis.await_count == 1
    assert out.spl_results_analysis is not None
    assert "execute_refine_exhausted" in (out.notes or [])


@pytest.mark.asyncio
async def test_execution_error_does_not_replace_query_with_zero_row_fallback(
    test_settings: Settings,
) -> None:
    settings = test_settings.model_copy(
        update={
            "tsoc_spl_execute_refine_max_attempts": 1,
            "tsoc_execute_investigation_spl": True,
            "splunk_username": "admin",
            "splunk_password": "x",
        }
    )
    original_spl = (
        'search index=firewall | eval is_benign=if(isnotnull(Sub_Status) '
        'AND (Sub_Status="Valid" OR Sub_Status="Trusted"),1,0) | table is_benign'
    )
    item = InvestigationQuestionItem(
        question="Is the signature valid?",
        spl=original_spl,
    )
    failed = SplSearchResult(
        row_count=0,
        rows=[],
        error="Error in EvalCommand: expression is malformed",
    )

    with (
        patch(
            "services.investigation.investigation_questions_spl.validate_investigation_question_items",
            new_callable=AsyncMock,
            side_effect=lambda _s, items, **_: items,
        ),
        patch(
            "services.investigation.investigation_questions_spl.execute_investigation_item",
            new_callable=AsyncMock,
            side_effect=lambda _s, it, **_: it.model_copy(
                update={"spl_results": failed}
            ),
        ),
        patch(
            "services.investigation.investigation_questions_spl.review_spl_after_execution_with_llm",
            new_callable=AsyncMock,
            return_value=(RootCauseSpl(spl=original_spl), False),
        ),
        patch(
            "services.investigation.investigation_questions_spl.build_zero_row_fallback_spl"
        ) as fallback,
        patch(
            "services.investigation.investigation_questions_spl.analyze_spl_execution_results_with_llm",
            new_callable=AsyncMock,
            return_value=None,
        ),
    ):
        out = await run_investigation_item_execute_refine_loop(
            settings,
            item,
            normalized={},
            search_name="test",
            sid="sid1",
            splunk_results=[],
            client=MagicMock(),
            session_key="sk",
        )

    fallback.assert_not_called()
    assert out.spl == original_spl
    assert out.spl_results is not None and out.spl_results.error
    assert "execute_refine_exhausted" in out.notes


def test_refine_sanitize_quotes_colon_values() -> None:
    from services.investigation.spl_tstats_sanitize import sanitize_spl_draft

    spl = (
        "search index=botsv1 sourcetype=XmlWinEventLog:Microsoft-Windows-Sysmon/Operational "
        "host=h1 | stats values(ParentImage)"
    )
    out = sanitize_spl_draft(spl)
    assert 'sourcetype="XmlWinEventLog:Microsoft-Windows-Sysmon/Operational"' in out
    assert "values(" not in out
    assert "dc(ParentImage)" in out


def test_build_zero_row_fallback_hash_question() -> None:
    from services.soc_analysis.soc_analysis_root_cause_spl import build_zero_row_fallback_spl

    rc = build_zero_row_fallback_spl(
        "What is the file hash for Image=C:\\Users\\Public\\invoke.ps1 on host=we8105desk?",
        {"index": "botsv1", "host": "we8105desk"},
    )
    assert rc is not None
    assert "EventCode=11" in rc.spl
    assert "invoke.ps1" in rc.spl
    assert "tstats" not in rc.spl.lower()
    assert "values(" not in rc.spl


@pytest.mark.asyncio
async def test_refine_loop_auto_fallback_when_llm_returns_tstats(test_settings: Settings) -> None:
    settings = test_settings.model_copy(
        update={
            "tsoc_spl_execute_refine_max_attempts": 1,
            "tsoc_execute_investigation_spl": True,
            "splunk_username": "admin",
            "splunk_password": "x",
        }
    )
    item = InvestigationQuestionItem(
        question="What is the file hash for Image=invoke.ps1 on host=we8105desk?",
        spl='search index=botsv1 host=we8105desk ParentCommandLine="*invoke.ps1*" | stats values(Hashes)',
    )
    zero = SplSearchResult(row_count=0, rows=[])
    bad_llm = RootCauseSpl(
        spl="| tstats from datamodel=Endpoint.Files | stats values(hash)",
        notes=["llm_refine_after_execute_1"],
    )
    rows = SplSearchResult(row_count=1, rows=[{"Hashes": "abc"}])

    client = MagicMock()

    async def _exec(_settings, it, **_) -> InvestigationQuestionItem:
        if "EventCode=11" in (it.spl or ""):
            return it.model_copy(update={"spl_results": rows})
        return it.model_copy(update={"spl_results": zero})

    exec_mock = AsyncMock(side_effect=_exec)
    with (
        patch(
            "services.investigation.investigation_questions_spl.validate_investigation_question_items",
            new_callable=AsyncMock,
            side_effect=lambda _s, items, **_: items,
        ),
        patch(
            "services.investigation.investigation_questions_spl.execute_investigation_item",
            exec_mock,
        ),
        patch(
            "services.investigation.investigation_questions_spl.review_spl_after_execution_with_llm",
            new_callable=AsyncMock,
            return_value=(bad_llm, True),
        ),
        patch(
            "services.investigation.investigation_questions_spl.analyze_spl_execution_results_with_llm",
            new_callable=AsyncMock,
            return_value={"summary": "hash observed", "usefulness": "high"},
        ),
    ):
        out = await run_investigation_item_execute_refine_loop(
            settings,
            item,
            normalized={"index": "botsv1", "host": "we8105desk"},
            search_name="test",
            sid="sid1",
            splunk_results=[],
            client=client,
            session_key="sk",
        )

    assert "auto_fallback_after_zero_rows" in (out.notes or [])
    assert out.spl_results_analysis is not None
    assert "llm_result_batch_analysis" in (out.notes or [])
    assert "EventCode=11" in (out.spl or "")
    assert exec_mock.await_count == 2
