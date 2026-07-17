"""Focused business tests for the verified incident-to-runbook workflow."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, patch

import pytest

from config import Settings
from models.analysis import InvestigationQuestionItem, RootCauseSplValidation, SplSearchResult
from models.runbook import (
    RunbookApproval,
    RunbookApprovalBody,
    RunbookExportBundle,
    RunbookImportBody,
    RunbookRevisionBody,
    RunbookRun,
    RunbookRunBody,
    RunbookShadowBody,
    RunbookShadowRun,
    RunbookStep,
    SafeResponseDecisionBody,
    SafeResponsePreview,
    SafeResponsePreviewBody,
    VerifiedRunbookDraft,
)
from services.investigation.verified_runbook import (
    VerifiedRunbookError,
    _first_execution_error,
    _get_source_record,
    _minimized_source_snapshot,
    _parse_compiled_payload,
    _parse_safe_response_payload,
    build_safe_response_preview,
    build_verified_runbook,
    derive_run_status,
    derive_source_status,
    get_runbook_runtime_status,
    get_runbook_evaluation,
    export_runbooks,
    import_runbooks,
    list_compatible_runbook_targets,
    list_runbook_library,
    record_runbook_approval,
    record_safe_response_decision,
    revise_runbook,
    run_verified_runbook,
    run_shadow_replay,
)


@pytest.fixture
def test_settings() -> Settings:
    return Settings(
        splunk_mgmt_url="https://127.0.0.1:8089",
        splunk_username="",
        splunk_password="",
        splunk_verify_ssl=False,
        tsoc_mcp_enabled=False,
        splunk_mcp_url=None,
        splunk_mcp_token=None,
        tsoc_spl_use_rest_predict=False,
        tsoc_investigation_questions_max=3,
        tsoc_postgres_dsn=None,
        tsoc_ingest_auto_analyze=False,
        litellm_api_key=None,
        litellm_api_base=None,
    )


@pytest.fixture(autouse=True)
def disable_background_runbook_rag_index():
    """Keep unit tests from starting the real FastEmbed/Qdrant background job."""
    with patch("services.soc_rag.index_writer.schedule_runbook_artifact_index"):
        yield


def _runtime_settings(settings: Settings) -> Settings:
    return settings.model_copy(
        update={
            "tsoc_postgres_dsn": "postgresql://demo",
            "litellm_model": "openai/gpt-5.6",
            "litellm_api_base": "http://llm.local",
            "splunk_username": "svc",
            "splunk_password": "secret",
            "tsoc_execute_investigation_spl": True,
        }
    )


def _record(record_id: int = 10, *, search_name: str = "Suspicious Login") -> dict:
    return {
        "id": record_id,
        "sid": f"sid-{record_id}",
        "row_index": 0,
        "search_name": search_name,
        "tsoc_record_type": "soc_analysis",
        "payload": {
            "analysis_input": {
                "alert_fields": {
                    "host": "source-host",
                    "user": "alice",
                    "api_token": "must-not-leave",
                }
            },
            "triage": {"review_verdict": "TRUE_POSITIVE"},
            "analysis": {
                "summary": "Repeated authentication failures followed by success",
                "defender": "Could be user error",
                "hunter": {"narrative": "Correlate authentication activity"},
                "judge": {
                    "verdict": "needs_investigation",
                    "recommended_next_step": "Review source activity",
                },
                "investigation_questions": [
                    {
                        "question": "Did the account authenticate from another source?",
                        "spl": "index=auth user=alice | head 20",
                        "explanation": "Source query",
                        "pivots": ["user"],
                    }
                ],
                "evidence_chain": {"decision": {"basis": "authentication sequence"}},
            },
        },
    }


def _step() -> RunbookStep:
    return RunbookStep(
        step_id="step-1",
        title="Correlate authentication",
        intent="Determine whether the affected identity authenticated from unusual sources.",
        expected_evidence="Authentication events grouped by identity and source.",
        stop_condition="Abstain when identity or source telemetry is unavailable.",
    )


def _draft(*, runbook_id: str = "rb-1", status: str = "SOURCE_VERIFIED") -> VerifiedRunbookDraft:
    return VerifiedRunbookDraft(
        runbook_id=runbook_id,
        source_record_id=10,
        title="Suspicious login investigation",
        summary="Correlate authentication evidence.",
        applicable_search_name="Suspicious Login",
        source_verdict="TRUE_POSITIVE",
        steps=[_step()],
        decision_rule="Escalate on corroborating evidence; otherwise abstain.",
        limitations=[],
        source_results=[_result(rows=2)],
        status=status,
        configured_model="openai/gpt-5.6",
        model="gpt-5.6-2026-07-01",
        compile_duration_ms=1200,
        created_at="2026-07-14T10:00:00+00:00",
    )


def _response_output(*, action_type: str = "ISOLATE_ENDPOINT") -> dict:
    return {
        "content": (
            "{"
            '"actions":[{'
            '"action_id":"action-1",'
            f'"action_type":"{action_type}",'
            '"title":"Contain the affected asset",'
            '"target_type":"endpoint",'
            '"target":"source-host",'
            '"risk_level":"high",'
            '"rationale":"The verified evidence indicates active malicious behavior.",'
            '"prerequisites":["Confirm business owner and incident severity"],'
            '"expected_effect":"Stop further network activity from the affected asset.",'
            '"rollback_plan":"Restore connectivity after eradication and owner approval.",'
            '"verification_steps":["Confirm the asset no longer communicates externally"],'
            '"requires_human_approval":true,'
            '"execution_mode":"PREVIEW_ONLY"'
            '}],'
            '"decision_summary":"Review the evidence and operational impact before manual action.",'
            '"limitations":["No action has been executed"]'
            "}"
        ),
        "model": "openai/gpt-5.6",
        "usage": {"prompt_tokens": 100, "completion_tokens": 50},
    }


def _result(*, parser_valid: bool = True, rows: int = 1, error: str | None = None) -> InvestigationQuestionItem:
    return InvestigationQuestionItem(
        question="Correlate authentication activity",
        spl="index=auth | head 20",
        validation=RootCauseSplValidation(
            method="splunk_parser", valid=parser_valid, message=None
        ),
        spl_results=SplSearchResult(
            row_count=rows,
            rows=[{"count": rows}] if rows else [],
            error=error,
        ),
    )


def test_deterministic_source_status() -> None:
    assert derive_source_status([_result(rows=3)]) == "SOURCE_VERIFIED"
    assert derive_source_status([_result(rows=0)]) == "PARSER_VALID"
    assert derive_source_status([_result(parser_valid=False)]) == "DRAFT"
    assert derive_source_status([_result(error="Splunk unavailable")]) == "FAILED"
    assert derive_source_status([]) == "DRAFT"
    assert derive_source_status([_result(rows=3)], expected_count=2) == "FAILED"


def test_deterministic_target_status() -> None:
    assert derive_run_status([_result(rows=2)]) == "REUSED"
    assert derive_run_status([_result(rows=0)]) == "NO_EVIDENCE"
    assert derive_run_status([_result(error="timeout")]) == "FAILED"
    assert derive_run_status([_result(rows=2)], expected_count=2) == "FAILED"


def test_first_execution_error_returns_safe_reason() -> None:
    assert _first_execution_error([_result(error="missing lookup")]) == "missing lookup"
    assert _first_execution_error([_result(rows=0)]) is None


def test_compiler_output_is_strict() -> None:
    valid = {
        "content": """{
          "title": "Login investigation",
          "summary": "Reusable authentication checks",
          "steps": [{
            "step_id": "step-1",
            "title": "Correlate",
            "intent": "Correlate identity authentication sources",
            "expected_evidence": "Events grouped by source",
            "stop_condition": "Abstain when data is missing"
          }],
          "decision_rule": "Escalate on corroboration, otherwise abstain",
          "limitations": []
        }"""
    }
    parsed = _parse_compiled_payload(valid)
    assert parsed.steps[0].step_id == "step-1"

    malformed = {"content": '{"title":"x","steps":[],"raw_spl":"| delete"}'}
    with pytest.raises(VerifiedRunbookError, match="invalid runbook"):
        _parse_compiled_payload(malformed)

    two_steps = {
        "content": """{
          "title":"Login investigation",
          "summary":"Reusable authentication checks",
          "steps":[
            {"step_id":"step-1","title":"Correlate","intent":"Correlate identity authentication sources","expected_evidence":"Events grouped by source","stop_condition":"Abstain when data is missing"},
            {"step_id":"step-2","title":"Confirm","intent":"Confirm the pattern with independent telemetry","expected_evidence":"Corroborating events","stop_condition":"Abstain when telemetry is unavailable"}
          ],
          "decision_rule":"Escalate on corroboration, otherwise abstain",
          "limitations":[]
        }""",
    }
    with pytest.raises(VerifiedRunbookError, match="configured maximum"):
        _parse_compiled_payload(two_steps, max_steps=1)


def test_safe_response_parser_enforces_allowlist_and_blocks_commands() -> None:
    parsed = _parse_safe_response_payload(
        _response_output(),
        allowed_action_types={"ISOLATE_ENDPOINT"},
    )
    assert parsed.actions[0].execution_mode == "PREVIEW_ONLY"
    assert parsed.actions[0].requires_human_approval is True

    with pytest.raises(VerifiedRunbookError, match="disallowed action"):
        _parse_safe_response_payload(
            _response_output(),
            allowed_action_types={"MONITOR_ONLY"},
        )

    command_output = _response_output()
    command_output["content"] = command_output["content"].replace(
        "The verified evidence indicates active malicious behavior.",
        "Run powershell Stop-Process after approval.",
    )
    with pytest.raises(VerifiedRunbookError, match="command or query syntax"):
        _parse_safe_response_payload(
            command_output,
            allowed_action_types={"ISOLATE_ENDPOINT"},
        )


@pytest.mark.asyncio
async def test_safe_response_preview_is_persisted_but_never_executable(
    test_settings: Settings,
) -> None:
    settings = _runtime_settings(test_settings)
    with (
        patch("services.investigation.verified_runbook.splunk_store_configured", return_value=True),
        patch(
            "services.investigation.verified_runbook._get_source_record",
            new_callable=AsyncMock,
            return_value=_record(),
        ),
        patch(
            "services.investigation.verified_runbook._latest_draft",
            new_callable=AsyncMock,
            return_value=_draft(),
        ),
        patch(
            "services.investigation.verified_runbook.litellm_chat_completion",
            new_callable=AsyncMock,
            return_value=_response_output(),
        ) as completion,
        patch(
            "services.investigation.verified_runbook.submit_hec_event",
            new_callable=AsyncMock,
            return_value=True,
        ) as submit,
    ):
        preview = await build_safe_response_preview(
            settings,
            10,
            SafeResponsePreviewBody(runbook_id="rb-1"),
        )

    assert preview.status == "READY_FOR_REVIEW"
    assert preview.evidence_basis == "SOURCE_EVIDENCE"
    assert preview.execution_supported is False
    assert preview.actions[0].action_type == "ISOLATE_ENDPOINT"
    assert preview.actions[0].execution_mode == "PREVIEW_ONLY"
    request_text = completion.await_args.args[1][1]["content"]
    assert "must-not-leave" not in request_text
    assert '"commands_queries_scripts_forbidden":true' in request_text
    event = submit.await_args.args[1]
    assert event["tsoc_record_type"] == "verified_runbook_response_preview"
    assert event["execution_supported"] is False


@pytest.mark.asyncio
async def test_safe_response_decision_approves_manual_action_only(
    test_settings: Settings,
) -> None:
    settings = _runtime_settings(test_settings)
    action = _parse_safe_response_payload(
        _response_output(),
        allowed_action_types={"ISOLATE_ENDPOINT"},
    ).actions[0]
    preview = SafeResponsePreview(
        preview_id="preview-1",
        runbook_id="rb-1",
        source_record_id=10,
        source_verdict="TRUE_POSITIVE",
        evidence_basis="SOURCE_EVIDENCE",
        actions=[action],
        decision_summary="Review before manual action.",
        model="openai/gpt-5.6",
        created_at="2026-07-15T10:00:00+00:00",
    )
    with (
        patch("services.investigation.verified_runbook.splunk_store_configured", return_value=True),
        patch(
            "services.investigation.verified_runbook.get_stored_event_by_id",
            new_callable=AsyncMock,
            return_value=_record(),
        ),
        patch(
            "services.investigation.verified_runbook._latest_draft",
            new_callable=AsyncMock,
            return_value=_draft(),
        ),
        patch(
            "services.investigation.verified_runbook._latest_response_preview",
            new_callable=AsyncMock,
            return_value=preview,
        ),
        patch(
            "services.investigation.verified_runbook.submit_hec_event",
            new_callable=AsyncMock,
            return_value=True,
        ) as submit,
    ):
        decision = await record_safe_response_decision(
            settings,
            10,
            SafeResponseDecisionBody(
                preview_id="preview-1",
                decision="approve_for_manual_action",
                analyst="alice",
                note="Targets, evidence, rollback, and change process reviewed.",
            ),
        )

    assert decision.decision == "approve_for_manual_action"
    assert decision.automatic_execution_performed is False
    event = submit.await_args.args[1]
    assert event["tsoc_record_type"] == "verified_runbook_response_decision"
    assert event["automatic_execution_performed"] is False


def test_runtime_status_exposes_policy_without_secrets(test_settings: Settings) -> None:
    settings = _runtime_settings(test_settings)
    with patch(
        "services.investigation.verified_runbook.splunk_store_configured",
        return_value=True,
    ):
        status = get_runbook_runtime_status(settings)
    assert status.ready is True
    assert status.max_steps == 3
    assert status.exact_search_name_required is True
    assert status.execution_transport_policy == "mcp_then_rest"
    assert status.rest_api_configured is True
    assert "secret" not in str(status.model_dump())


@pytest.mark.asyncio
async def test_source_eligibility_rejects_unacknowledged(test_settings: Settings) -> None:
    with (
        patch(
            "services.investigation.verified_runbook.get_stored_event_by_id",
            new_callable=AsyncMock,
            return_value=_record(),
        ),
        patch(
            "services.investigation.verified_runbook.list_analyst_actions_for_record",
            new_callable=AsyncMock,
            return_value=[{"action": "escalate"}],
        ),
    ):
        with pytest.raises(VerifiedRunbookError, match="Acknowledge"):
            await _get_source_record(test_settings, 10)


@pytest.mark.asyncio
async def test_source_eligibility_rejects_false_positive(test_settings: Settings) -> None:
    row = _record()
    row["payload"]["triage"]["review_verdict"] = "FALSE_POSITIVE"
    with patch(
        "services.investigation.verified_runbook.get_stored_event_by_id",
        new_callable=AsyncMock,
        return_value=row,
    ):
        with pytest.raises(VerifiedRunbookError, match="False-positive"):
            await _get_source_record(test_settings, 10)


@pytest.mark.asyncio
async def test_compatible_targets_are_exact_minimal_and_bounded(
    test_settings: Settings,
) -> None:
    settings = _runtime_settings(test_settings).model_copy(
        update={"tsoc_runbook_artifact_scan_limit": 1000}
    )
    compatible = _record(20)
    compatible["created_at"] = "2026-07-14T11:00:00+00:00"
    different = _record(21, search_name="Different Detection")
    duplicate_sid = _record(22)
    duplicate_sid["sid"] = "sid-10"
    with (
        patch(
            "services.investigation.verified_runbook.splunk_store_configured",
            return_value=True,
        ),
        patch(
            "services.investigation.verified_runbook.get_stored_event_by_id",
            new_callable=AsyncMock,
            return_value=_record(),
        ),
        patch(
            "services.investigation.verified_runbook.search_stored_events",
            new_callable=AsyncMock,
            return_value=[_record(), duplicate_sid, different, compatible],
        ) as search,
    ):
        targets = await list_compatible_runbook_targets(settings, 10, limit=5)

    assert targets.count == 1
    assert targets.results[0].record_id == 20
    assert targets.results[0].sid == "sid-20"
    assert targets.results[0].search_name == "Suspicious Login"
    assert targets.results[0].summary == "Repeated authentication failures followed by success"
    assert "payload" not in targets.results[0].model_dump()
    assert search.await_args.kwargs["limit"] == 1000


@pytest.mark.asyncio
@pytest.mark.parametrize("mutation, message", [("type", "soc_analysis"), ("questions", "questions")])
async def test_source_eligibility_rejects_wrong_type_or_empty_questions(
    test_settings: Settings, mutation: str, message: str
) -> None:
    row = _record()
    if mutation == "type":
        row["tsoc_record_type"] = "observability_analysis"
    else:
        row["payload"]["analysis"]["investigation_questions"] = []
    with patch(
        "services.investigation.verified_runbook.get_stored_event_by_id",
        new_callable=AsyncMock,
        return_value=row,
    ):
        with pytest.raises(VerifiedRunbookError, match=message):
            await _get_source_record(test_settings, 10)


def test_source_snapshot_omits_raw_spl_and_unrelated_payload() -> None:
    row = _record()
    row["payload"]["raw_alert"] = {"credential": "must-not-leave-either"}
    row["payload"]["analysis"]["evidence_chain"]["nested"] = {
        "authorization": "must-not-leave-nested"
    }
    snapshot = _minimized_source_snapshot(row)
    encoded = str(snapshot)
    assert "must-not-leave" not in encoded
    assert "index=auth" not in encoded
    assert snapshot["source"]["alert_fields"]["host"] == "source-host"


@pytest.mark.asyncio
async def test_build_compiles_executes_and_persists(
    test_settings: Settings,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(
        logging.INFO,
        logger="services.investigation.verified_runbook",
    )
    settings = _runtime_settings(test_settings)
    llm_output = {
        "content": """{
          "title":"Suspicious login investigation",
          "summary":"Correlate authentication activity",
          "steps":[{
            "step_id":"step-1",
            "title":"Correlate authentication",
            "intent":"Determine whether the affected identity authenticated from unusual sources.",
            "expected_evidence":"Authentication events grouped by identity and source.",
            "stop_condition":"Abstain when identity or source telemetry is unavailable."
          }],
          "decision_rule":"Escalate on corroboration; otherwise abstain.",
          "limitations":[]
        }""",
        "model": "gpt-5.6-2026-07-01",
        "usage": {"prompt_tokens": 100, "completion_tokens": 80},
    }
    with (
        patch("services.investigation.verified_runbook.splunk_store_configured", return_value=True),
        patch(
            "services.investigation.verified_runbook.get_stored_event_by_id",
            new_callable=AsyncMock,
            return_value=_record(),
        ),
        patch(
            "services.investigation.verified_runbook.list_analyst_actions_for_record",
            new_callable=AsyncMock,
            return_value=[{"action": "acknowledge"}],
        ),
        patch(
            "services.investigation.verified_runbook.litellm_chat_completion",
            new_callable=AsyncMock,
            return_value=llm_output,
        ),
        patch(
            "services.investigation.verified_runbook._finalize_steps",
            new_callable=AsyncMock,
            return_value=[_result(rows=2)],
        ) as finalize,
        patch(
            "services.investigation.verified_runbook.submit_hec_event",
            new_callable=AsyncMock,
            return_value=True,
        ) as submit,
        patch(
            "services.investigation.verified_runbook._latest_draft",
            new_callable=AsyncMock,
            return_value=None,
        ),
    ):
        draft = await build_verified_runbook(settings, 10)

    assert draft.status == "SOURCE_VERIFIED"
    assert draft.model == "gpt-5.6-2026-07-01"
    assert draft.prompt_tokens == 100
    assert draft.parser_valid_step_count == 1
    assert draft.successful_step_count == 1
    assert draft.total_evidence_rows == 2
    assert finalize.await_args.kwargs["normalized"]["host"] == "source-host"
    assert finalize.await_args.kwargs["max_items"] == settings.tsoc_runbook_max_steps
    event = submit.await_args.args[1]
    assert event["tsoc_record_type"] == "verified_runbook_draft"
    assert event["source_record_id"] == 10
    logs = "\n".join(record.getMessage() for record in caplog.records)
    assert "runbook_event=compile.requested" in logs
    assert "runbook_event=compile.generation_completed" in logs
    assert "runbook_event=compile.verification_completed" in logs
    assert "runbook_event=artifact.persisted" in logs
    assert "runbook_event=compile.completed" in logs
    assert "must-not-leave" not in logs
    assert "index=auth" not in logs


@pytest.mark.asyncio
async def test_library_groups_all_revisions_and_attaches_gate_state(
    test_settings: Settings,
) -> None:
    first = _draft(runbook_id="rb-1")
    second = _draft(runbook_id="rb-2").model_copy(
        update={"revision": 2, "parent_runbook_id": "rb-1"}
    )
    other_sid_source = _draft(runbook_id="rb-other-sid").model_copy(
        update={"source_record_id": 20}
    )
    approval = RunbookApproval(
        runbook_id="rb-2",
        source_record_id=10,
        decision="approve",
        created_at="2026-07-14T11:00:00+00:00",
    )

    async def rows(_settings: Settings, record_type: str) -> list[dict]:
        if record_type == "verified_runbook_draft":
            return [
                {"payload": second.model_dump()},
                {"payload": first.model_dump()},
                {"payload": other_sid_source.model_dump()},
            ]
        if record_type == "verified_runbook_approval":
            return [{"payload": approval.model_dump()}]
        return []

    with (
        patch("services.investigation.verified_runbook.splunk_store_configured", return_value=True),
        patch("services.investigation.verified_runbook._artifact_rows", side_effect=rows),
    ):
        library = await list_runbook_library(test_settings)

    assert library.alert_count == 1
    assert library.count == 3
    assert [item.draft.runbook_id for item in library.groups[0].runbooks] == [
        "rb-2",
        "rb-1",
        "rb-other-sid",
    ]
    assert library.groups[0].runbooks[0].latest_approval is not None
    assert library.groups[0].runbooks[0].is_latest_for_source is True
    assert library.groups[0].runbooks[1].is_latest_for_source is False
    assert library.groups[0].runbooks[2].is_latest_for_source is True


@pytest.mark.asyncio
async def test_export_is_portable_and_excludes_evidence_and_approval(
    test_settings: Settings,
) -> None:
    draft = _draft()
    with patch(
        "services.investigation.verified_runbook.list_runbook_library",
        new_callable=AsyncMock,
    ) as list_library:
        from models.runbook import RunbookLibraryGroup, RunbookLibraryItem, RunbookLibraryResponse

        list_library.return_value = RunbookLibraryResponse(
            count=1,
            alert_count=1,
            groups=[
                RunbookLibraryGroup(
                    alert_name="Suspicious Login",
                    count=1,
                    runbooks=[RunbookLibraryItem(draft=draft)],
                )
            ],
        )
        document = await export_runbooks(test_settings, runbook_id="rb-1")

    encoded = document.model_dump(mode="json")
    assert encoded["schema_version"] == "thinking-soc.runbook-library/v1"
    assert "source_results" not in encoded["runbooks"][0]
    assert "latest_approval" not in str(encoded)
    assert encoded["runbooks"][0]["applicable_search_name"] == "Suspicious Login"


@pytest.mark.asyncio
async def test_import_without_source_is_an_inert_draft(test_settings: Settings) -> None:
    portable = RunbookExportBundle(
        exported_at="2026-07-14T10:00:00+00:00",
        runbooks=[
            {
                "title": "Imported login checks",
                "summary": "Portable intent-only checks",
                "applicable_search_name": "Suspicious Login",
                "steps": [_step().model_dump()],
                "decision_rule": "Escalate on corroboration; otherwise abstain.",
                "limitations": [],
            }
        ],
    )
    with (
        patch("services.investigation.verified_runbook.splunk_store_configured", return_value=True),
        patch(
            "services.investigation.verified_runbook.submit_hec_event",
            new_callable=AsyncMock,
            return_value=True,
        ) as submit,
    ):
        result = await import_runbooks(
            test_settings, RunbookImportBody(document=portable)
        )

    imported = result.runbooks[0]
    assert imported.status == "DRAFT"
    assert imported.source_record_id == 0
    assert imported.origin == "imported"
    assert imported.source_results == []
    assert submit.await_args.args[1]["search_name"] == "Suspicious Login"


@pytest.mark.asyncio
async def test_edit_creates_revision_and_resets_verification(
    test_settings: Settings,
) -> None:
    parent = _draft().model_copy(update={"source_record_id": 0})
    body = RunbookRevisionBody(
        title="Updated login checks",
        summary=parent.summary,
        applicable_search_name=parent.applicable_search_name,
        steps=parent.steps,
        decision_rule=parent.decision_rule,
        limitations=[],
        revision_note="Tighten analyst guidance",
    )
    with (
        patch("services.investigation.verified_runbook.splunk_store_configured", return_value=True),
        patch(
            "services.investigation.verified_runbook._draft_by_id",
            new_callable=AsyncMock,
            return_value=parent,
        ),
        patch(
            "services.investigation.verified_runbook.submit_hec_event",
            new_callable=AsyncMock,
            return_value=True,
        ),
    ):
        revised = await revise_runbook(test_settings, parent.runbook_id, body)

    assert revised.runbook_id != parent.runbook_id
    assert revised.parent_runbook_id == parent.runbook_id
    assert revised.revision == 2
    assert revised.status == "DRAFT"
    assert revised.source_results == []


@pytest.mark.asyncio
async def test_disabled_feature_stops_before_provider_calls(test_settings: Settings) -> None:
    settings = _runtime_settings(test_settings).model_copy(
        update={"tsoc_runbook_enabled": False}
    )
    with patch(
        "services.investigation.verified_runbook.litellm_chat_completion",
        new_callable=AsyncMock,
    ) as llm:
        with pytest.raises(VerifiedRunbookError, match="disabled"):
            await build_verified_runbook(settings, 10)
    llm.assert_not_awaited()


@pytest.mark.asyncio
async def test_approval_rejects_stale_runbook(test_settings: Settings) -> None:
    with (
        patch("services.investigation.verified_runbook.splunk_store_configured", return_value=True),
        patch(
            "services.investigation.verified_runbook.get_stored_event_by_id",
            new_callable=AsyncMock,
            return_value=_record(),
        ),
        patch(
            "services.investigation.verified_runbook._latest_draft",
            new_callable=AsyncMock,
            return_value=_draft(runbook_id="latest"),
        ),
    ):
        with pytest.raises(VerifiedRunbookError, match="latest"):
            await record_runbook_approval(
                test_settings,
                10,
                RunbookApprovalBody(runbook_id="old", decision="approve"),
            )


@pytest.mark.asyncio
async def test_reuse_requires_exact_search_name(test_settings: Settings) -> None:
    settings = _runtime_settings(test_settings)

    async def stored_record(_settings: Settings, record_id: int) -> dict:
        if record_id == 10:
            return _record(10)
        return _record(20, search_name="Different Detection")

    with (
        patch("services.investigation.verified_runbook.splunk_store_configured", return_value=True),
        patch(
            "services.investigation.verified_runbook.get_stored_event_by_id",
            new_callable=AsyncMock,
            side_effect=stored_record,
        ),
        patch(
            "services.investigation.verified_runbook._latest_draft",
            new_callable=AsyncMock,
            return_value=_draft(),
        ),
        patch(
            "services.investigation.verified_runbook._latest_approval",
            new_callable=AsyncMock,
            return_value=RunbookApproval(
                runbook_id="rb-1",
                source_record_id=10,
                decision="approve",
                created_at="2026-07-14T10:01:00+00:00",
            ),
        ),
    ):
        with pytest.raises(VerifiedRunbookError, match="search_name"):
            await run_verified_runbook(
                settings,
                20,
                RunbookRunBody(source_record_id=10, runbook_id="rb-1"),
            )


@pytest.mark.asyncio
async def test_reuse_rejects_duplicate_sid_even_when_record_id_differs(
    test_settings: Settings,
) -> None:
    settings = _runtime_settings(test_settings)
    source = _record(10)
    duplicate = _record(20)
    duplicate["sid"] = source["sid"]

    async def stored_record(_settings: Settings, record_id: int) -> dict:
        return source if record_id == 10 else duplicate

    with (
        patch("services.investigation.verified_runbook.splunk_store_configured", return_value=True),
        patch(
            "services.investigation.verified_runbook.get_stored_event_by_id",
            new_callable=AsyncMock,
            side_effect=stored_record,
        ),
    ):
        with pytest.raises(VerifiedRunbookError, match="different Splunk SID"):
            await run_verified_runbook(
                settings,
                20,
                RunbookRunBody(source_record_id=10, runbook_id="rb-1"),
            )


@pytest.mark.asyncio
async def test_reuse_calculates_time_saved(
    test_settings: Settings,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(
        logging.INFO,
        logger="services.investigation.verified_runbook",
    )
    settings = _runtime_settings(test_settings)

    async def stored_record(_settings: Settings, record_id: int) -> dict:
        return _record(record_id)

    with (
        patch("services.investigation.verified_runbook.splunk_store_configured", return_value=True),
        patch(
            "services.investigation.verified_runbook.get_stored_event_by_id",
            new_callable=AsyncMock,
            side_effect=stored_record,
        ),
        patch(
            "services.investigation.verified_runbook._latest_draft",
            new_callable=AsyncMock,
            return_value=_draft(),
        ),
        patch(
            "services.investigation.verified_runbook._latest_approval",
            new_callable=AsyncMock,
            return_value=RunbookApproval(
                runbook_id="rb-1",
                source_record_id=10,
                decision="approve",
                created_at="2026-07-14T10:01:00+00:00",
            ),
        ),
        patch(
            "services.investigation.verified_runbook._finalize_steps",
            new_callable=AsyncMock,
            return_value=[_result(rows=4)],
        ) as finalize,
        patch(
            "services.investigation.verified_runbook.submit_hec_event",
            new_callable=AsyncMock,
            return_value=True,
        ),
    ):
        run = await run_verified_runbook(
            settings,
            20,
            RunbookRunBody(
                source_record_id=10,
                runbook_id="rb-1",
                estimated_manual_minutes=25,
            ),
        )

    assert run.status == "REUSED"
    assert 0 <= run.estimated_minutes_saved <= 25
    assert 0 <= run.savings_percent <= 100
    assert run.successful_step_count == 1
    assert run.total_evidence_rows == 4
    assert run.target_record_id == 20
    assert finalize.await_args.kwargs["max_items"] == 1
    logs = "\n".join(record.getMessage() for record in caplog.records)
    assert "runbook_event=reuse.requested" in logs
    assert "runbook_event=reuse.execution_started" in logs
    assert "runbook_event=reuse.execution_completed" in logs
    assert "runbook_event=reuse.completed" in logs


@pytest.mark.asyncio
async def test_shadow_replay_runs_unapproved_draft_on_distinct_sid(
    test_settings: Settings,
) -> None:
    settings = _runtime_settings(test_settings).model_copy(
        update={"tsoc_runbook_analyst_hourly_cost_usd": 60.0}
    )

    async def stored_record(_settings: Settings, record_id: int) -> dict:
        return _record(record_id)

    with (
        patch("services.investigation.verified_runbook.splunk_store_configured", return_value=True),
        patch(
            "services.investigation.verified_runbook.get_stored_event_by_id",
            new_callable=AsyncMock,
            side_effect=stored_record,
        ),
        patch(
            "services.investigation.verified_runbook._draft_by_id",
            new_callable=AsyncMock,
            return_value=_draft(status="PARSER_VALID"),
        ),
        patch(
            "services.investigation.verified_runbook._finalize_steps",
            new_callable=AsyncMock,
            return_value=[_result(rows=3)],
        ) as finalize,
        patch(
            "services.investigation.verified_runbook.submit_hec_event",
            new_callable=AsyncMock,
            return_value=True,
        ) as submit,
    ):
        shadow = await run_shadow_replay(
            settings,
            20,
            RunbookShadowBody(
                source_record_id=10,
                runbook_id="rb-1",
                estimated_manual_minutes=25,
            ),
        )

    assert shadow.status == "EVIDENCE_FOUND"
    assert shadow.source_sid == "sid-10"
    assert shadow.target_sid == "sid-20"
    assert shadow.parser_valid_step_count == 1
    assert shadow.successful_step_count == 1
    assert shadow.total_evidence_rows == 3
    assert shadow.execution_error_count == 0
    assert finalize.await_args.kwargs["max_items"] == 1
    assert 0 < shadow.projected_minutes_saved <= 25
    assert 0 < shadow.projected_labor_savings_usd <= 25
    event = submit.await_args.args[1]
    assert event["tsoc_record_type"] == "verified_runbook_shadow_run"
    assert event["sid"] == "sid-20"


@pytest.mark.asyncio
async def test_shadow_replay_rejects_duplicate_sid(test_settings: Settings) -> None:
    settings = _runtime_settings(test_settings)
    source = _record(10)
    target = _record(20)
    target["sid"] = source["sid"]

    async def stored_record(_settings: Settings, record_id: int) -> dict:
        return source if record_id == 10 else target

    with (
        patch("services.investigation.verified_runbook.splunk_store_configured", return_value=True),
        patch(
            "services.investigation.verified_runbook.get_stored_event_by_id",
            new_callable=AsyncMock,
            side_effect=stored_record,
        ),
    ):
        with pytest.raises(VerifiedRunbookError, match="different Splunk SID"):
            await run_shadow_replay(
                settings,
                20,
                RunbookShadowBody(source_record_id=10, runbook_id="rb-1"),
            )


@pytest.mark.asyncio
async def test_evaluation_aggregates_quality_evidence_time_and_cost(
    test_settings: Settings,
) -> None:
    settings = _runtime_settings(test_settings).model_copy(
        update={
            "tsoc_runbook_analyst_hourly_cost_usd": 60.0,
            "tsoc_runbook_input_cost_per_1m_tokens": 1.0,
            "tsoc_runbook_output_cost_per_1m_tokens": 2.0,
        }
    )
    draft = _draft().model_copy(
        update={
            "prompt_tokens": 1000,
            "completion_tokens": 500,
            "parser_valid_step_count": 1,
        }
    )
    approval = RunbookApproval(
        runbook_id="rb-1",
        source_record_id=10,
        decision="approve",
        created_at="2026-07-14T10:01:00+00:00",
    )
    production = RunbookRun(
        runbook_id="rb-1",
        source_record_id=10,
        target_record_id=20,
        status="REUSED",
        results=[_result(rows=2)],
        duration_ms=1000,
        estimated_manual_minutes=25,
        estimated_minutes_saved=24.9,
        savings_percent=99.6,
        successful_step_count=1,
        total_evidence_rows=2,
        created_at="2026-07-14T10:02:00+00:00",
    )
    shadow = RunbookShadowRun(
        shadow_run_id="shadow-1",
        runbook_id="rb-1",
        source_record_id=10,
        target_record_id=21,
        source_sid="sid-10",
        target_sid="sid-21",
        search_name="Suspicious Login",
        status="EVIDENCE_FOUND",
        results=[_result(rows=4)],
        duration_ms=2000,
        estimated_manual_minutes=25,
        projected_minutes_saved=24.9,
        projected_labor_savings_usd=24.9,
        parser_valid_step_count=1,
        successful_step_count=1,
        total_evidence_rows=4,
        execution_error_count=0,
        created_at="2026-07-14T10:03:00+00:00",
    )

    async def rows(_settings: Settings, record_type: str) -> list[dict]:
        values = {
            "verified_runbook_draft": [draft],
            "verified_runbook_approval": [approval],
            "verified_runbook_run": [production],
            "verified_runbook_shadow_run": [shadow],
        }
        return [{"payload": item.model_dump()} for item in values.get(record_type, [])]

    with (
        patch("services.investigation.verified_runbook.splunk_store_configured", return_value=True),
        patch("services.investigation.verified_runbook._artifact_rows", side_effect=rows),
    ):
        evaluation = await get_runbook_evaluation(settings)

    assert evaluation.revision_count == 1
    assert evaluation.shadow_run_count == 1
    assert evaluation.production_run_count == 1
    assert evaluation.parser_valid_rate == 100
    assert evaluation.evidence_coverage_rate == 100
    assert evaluation.total_shadow_evidence_rows == 4
    assert evaluation.projected_labor_savings_usd == 24.9
    assert evaluation.realized_minutes_saved == 24.9
    assert evaluation.estimated_compile_llm_cost_usd == 0.002
    assert evaluation.recent_shadow_runs[0].shadow_run_id == "shadow-1"
