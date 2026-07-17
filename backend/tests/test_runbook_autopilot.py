"""Runbook Autopilot orchestration and Chat compaction tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from config import Settings
from models.runbook import (
    RunbookAutopilotBody,
    RunbookLibraryResponse,
    SafeResponseAction,
    SafeResponsePreview,
    VerifiedRunbookDraft,
    VerifiedRunbookState,
    RunbookStep,
)
from services.investigation.runbook_autopilot import run_runbook_autopilot
from services.soc_rag.compact_runbook import compact_runbook_artifact


def _settings() -> Settings:
    return Settings(
        tsoc_postgres_dsn="postgresql://test",
        litellm_model="openai/test",
        litellm_api_base="http://llm.local",
        splunk_username="svc",
        splunk_password="secret",
        tsoc_runbook_autopilot_enabled=True,
    )


def _source() -> dict:
    return {
        "id": 10,
        "sid": "sid-10",
        "search_name": "Suspicious Login",
        "row_index": 0,
        "tsoc_record_type": "soc_analysis",
        "payload": {},
    }


def _draft() -> VerifiedRunbookDraft:
    return VerifiedRunbookDraft(
        runbook_id="rb-1",
        source_record_id=10,
        title="Suspicious login investigation",
        summary="Correlate authentication evidence.",
        applicable_search_name="Suspicious Login",
        source_verdict="TRUE_POSITIVE",
        steps=[
            RunbookStep(
                step_id="step-1",
                title="Correlate authentication",
                intent="Find unusual sources.",
                expected_evidence="Authentication events.",
                stop_condition="Abstain without telemetry.",
            )
        ],
        decision_rule="Escalate on corroboration.",
        status="SOURCE_VERIFIED",
        model="test",
        compile_duration_ms=10,
        created_at="2026-07-15T10:00:00+00:00",
    )


def _preview() -> SafeResponsePreview:
    return SafeResponsePreview(
        preview_id="preview-1",
        runbook_id="rb-1",
        source_record_id=10,
        source_verdict="TRUE_POSITIVE",
        evidence_basis="SOURCE_EVIDENCE",
        actions=[
            SafeResponseAction(
                action_id="action-1",
                action_type="MONITOR_ONLY",
                title="Monitor the identity",
                target_type="identity",
                target="alice",
                risk_level="low",
                rationale="Observe for recurrence.",
                expected_effect="Improve confidence.",
                rollback_plan="Stop enhanced monitoring.",
                verification_steps=["Review new events"],
            )
        ],
        decision_summary="Review manually.",
        model="test",
        created_at="2026-07-15T10:01:00+00:00",
    )


@pytest.mark.asyncio
async def test_autopilot_reuses_preview_and_never_executes() -> None:
    state = VerifiedRunbookState(
        record_id=10,
        draft=_draft(),
        latest_response_preview=_preview(),
    )
    with (
        patch(
            "services.investigation.runbook_autopilot.get_stored_event_by_id",
            new_callable=AsyncMock,
            return_value=_source(),
        ),
        patch(
            "services.investigation.runbook_autopilot.list_analyst_actions_for_record",
            new_callable=AsyncMock,
            return_value=[{"action": "acknowledge"}],
        ),
        patch(
            "services.investigation.runbook_autopilot.get_verified_runbook_state",
            new_callable=AsyncMock,
            return_value=state,
        ),
        patch(
            "services.investigation.runbook_autopilot.list_runbook_library",
            new_callable=AsyncMock,
            return_value=RunbookLibraryResponse(count=1, alert_count=1),
        ),
        patch(
            "services.investigation.runbook_autopilot._persist_session",
            new_callable=AsyncMock,
        ) as persist,
        patch(
            "services.investigation.runbook_autopilot.build_verified_runbook",
            new_callable=AsyncMock,
        ) as compile_runbook,
        patch(
            "services.investigation.runbook_autopilot.build_safe_response_preview",
            new_callable=AsyncMock,
        ) as generate_preview,
    ):
        session = await run_runbook_autopilot(
            _settings(),
            10,
            RunbookAutopilotBody(),
        )

    assert session.status == "AWAITING_HUMAN_APPROVAL"
    assert session.response_preview_id == "preview-1"
    assert session.automatic_execution_performed is False
    assert session.human_approval_required is True
    assert "SUPERVISOR" in session.agents
    assert "POLICY_GUARD" in session.agents
    assert "runbook.safe_response_preview.cache" in session.tools_used
    assert any(event.kind == "HANDOFF" for event in session.trace)
    compile_runbook.assert_not_awaited()
    generate_preview.assert_not_awaited()
    persist.assert_awaited_once()


@pytest.mark.asyncio
async def test_autopilot_stops_before_generation_without_acknowledgment() -> None:
    with (
        patch(
            "services.investigation.runbook_autopilot.get_stored_event_by_id",
            new_callable=AsyncMock,
            return_value=_source(),
        ),
        patch(
            "services.investigation.runbook_autopilot.list_analyst_actions_for_record",
            new_callable=AsyncMock,
            return_value=[{"action": "escalate"}],
        ),
        patch(
            "services.investigation.runbook_autopilot.get_verified_runbook_state",
            new_callable=AsyncMock,
            return_value=VerifiedRunbookState(record_id=10),
        ),
        patch(
            "services.investigation.runbook_autopilot.list_runbook_library",
            new_callable=AsyncMock,
            return_value=RunbookLibraryResponse(count=0, alert_count=0),
        ),
        patch(
            "services.investigation.runbook_autopilot._persist_session",
            new_callable=AsyncMock,
        ),
        patch(
            "services.investigation.runbook_autopilot.build_verified_runbook",
            new_callable=AsyncMock,
        ) as compile_runbook,
    ):
        session = await run_runbook_autopilot(
            _settings(),
            10,
            RunbookAutopilotBody(),
        )

    assert session.status == "BLOCKED"
    assert "Acknowledge" in session.next_recommended_action
    assert session.automatic_execution_performed is False
    compile_runbook.assert_not_awaited()


def test_runbook_compaction_is_chat_ready_and_excludes_raw_execution() -> None:
    event = {
        "sid": "sid-10",
        "search_name": "Suspicious Login",
        **_draft().model_dump(mode="json"),
        "source_results": [
            {
                "spl": "index=secret password=must-not-index",
                "spl_results": {"rows": [{"api_token": "must-not-index"}]},
            }
        ],
    }
    doc = compact_runbook_artifact("verified_runbook_draft", event)

    assert doc is not None
    assert doc.doc_type == "runbook_draft"
    assert "Suspicious login investigation" in doc.chunk_text
    assert "Step 1" in doc.chunk_text
    assert "must-not-index" not in doc.chunk_text
    assert doc.essential["runbook_id"] == "rb-1"
