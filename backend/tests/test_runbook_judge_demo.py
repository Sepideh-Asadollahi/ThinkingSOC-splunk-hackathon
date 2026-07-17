"""Contract tests for the additive Runbook judge-tour demo bundle."""

from __future__ import annotations

import json
from pathlib import Path

from models.runbook import (
    RunbookApproval,
    RunbookAutopilotSession,
    RunbookRun,
    RunbookShadowRun,
    SafeResponseDecision,
    SafeResponsePreview,
    VerifiedRunbookDraft,
)
from services.demo.runbook_judge_demo import (
    AUTOPILOT_SESSION_ID,
    PREVIEW_ID,
    RUNBOOK_ID,
    SCENARIO_ID,
    SEARCH_NAME,
    SOURCE_SID,
    TARGET_SID,
    build_artifact_events,
)


def _by_type(events: list[dict], record_type: str) -> dict:
    return next(event for event in events if event["tsoc_record_type"] == record_type)


def test_judge_demo_artifacts_form_a_complete_safe_flow() -> None:
    events = build_artifact_events(source_record_id=901, target_record_id=902)
    draft = VerifiedRunbookDraft.model_validate(_by_type(events, "verified_runbook_draft"))
    approval = RunbookApproval.model_validate(_by_type(events, "verified_runbook_approval"))
    shadow = RunbookShadowRun.model_validate(_by_type(events, "verified_runbook_shadow_run"))
    run = RunbookRun.model_validate(_by_type(events, "verified_runbook_run"))
    preview = SafeResponsePreview.model_validate(
        _by_type(events, "verified_runbook_response_preview")
    )
    decision = SafeResponseDecision.model_validate(
        _by_type(events, "verified_runbook_response_decision")
    )
    autopilot = RunbookAutopilotSession.model_validate(
        _by_type(events, "verified_runbook_autopilot_session")
    )

    assert len(events) == 7
    assert SOURCE_SID != TARGET_SID
    assert all(event["search_name"] == SEARCH_NAME for event in events)
    assert all(event["demo_scenario_id"] == SCENARIO_ID for event in events)
    assert draft.runbook_id == RUNBOOK_ID
    assert draft.status == "SOURCE_VERIFIED"
    assert len(draft.steps) == 3
    assert draft.parser_valid_step_count == draft.successful_step_count == 3
    assert draft.total_evidence_rows == 3
    assert all(item.validation and item.validation.valid for item in draft.source_results)
    assert {item.spl_results.execution_transport for item in draft.source_results} == {"mcp", "rest"}
    assert all(item.spl.lstrip().startswith("search ") for item in draft.source_results)
    assert approval.decision == "approve"
    assert shadow.status == "EVIDENCE_FOUND"
    assert shadow.source_sid != shadow.target_sid
    assert run.status == "REUSED"
    assert run.source_record_id == 901 and run.target_record_id == 902
    assert preview.preview_id == PREVIEW_ID
    assert preview.execution_supported is False
    assert all(action.requires_human_approval for action in preview.actions)
    assert all(action.execution_mode == "PREVIEW_ONLY" for action in preview.actions)
    assert decision.automatic_execution_performed is False
    assert autopilot.session_id == AUTOPILOT_SESSION_ID
    assert autopilot.status == "COMPLETED"
    assert len(autopilot.agents) == 5
    assert {event.agent for event in autopilot.trace} == set(autopilot.agents)
    assert any(event.kind == "HANDOFF" for event in autopilot.trace)
    assert "splunk.mcp.search" in autopilot.tools_used
    assert "splunk.rest.oneshot_fallback" in autopilot.tools_used
    assert autopilot.human_approval_required is True
    assert autopilot.automatic_execution_performed is False


def test_committed_install_snapshot_contains_linked_judge_tour() -> None:
    snapshot = Path(__file__).resolve().parents[1] / "data" / "demo" / "postgres_snapshot"
    manifest = json.loads((snapshot / "manifest.json").read_text(encoding="utf-8"))
    records_path = snapshot / "tsoc_records.json"
    records = json.loads(records_path.read_text(encoding="utf-8"))
    scenario = [
        row
        for row in records
        if isinstance(row.get("payload"), dict)
        and row["payload"].get("demo_scenario_id") == SCENARIO_ID
    ]
    assert manifest["demo_mode"] == "full"
    manifest_tables = {entry["name"]: entry["rows"] for entry in manifest["tables"]}
    assert manifest_tables["tsoc_records"] == len(records)
    assert manifest_tables["tsoc_rag_documents"] >= 9
    assert manifest_tables["tsoc_chat_conversations"] >= 1
    assert manifest_tables["tsoc_chat_messages"] >= 2
    assert len(scenario) == 10
    types = {row["tsoc_record_type"] for row in scenario}
    assert {
        "soc_analysis",
        "investigation_analyst_action",
        "verified_runbook_draft",
        "verified_runbook_approval",
        "verified_runbook_shadow_run",
        "verified_runbook_run",
        "verified_runbook_response_preview",
        "verified_runbook_response_decision",
        "verified_runbook_autopilot_session",
    } <= types
    analyses = [row for row in scenario if row["tsoc_record_type"] == "soc_analysis"]
    assert {row["sid"] for row in analyses} == {SOURCE_SID, TARGET_SID}
    assert {row["search_name"] for row in analyses} == {SEARCH_NAME}

    rag_docs = json.loads(
        (snapshot / "tsoc_rag_documents.json").read_text(encoding="utf-8")
    )
    assert sum(doc.get("search_name") == SEARCH_NAME for doc in rag_docs) >= 9
    chat_messages = json.loads(
        (snapshot / "tsoc_chat_messages.json").read_text(encoding="utf-8")
    )
    judge_chat = [
        message
        for message in chat_messages
        if message.get("conversation_id") == "demo-runbook-judge-tour-v1"
    ]
    assert [message["role"] for message in judge_chat] == ["user", "assistant"]
