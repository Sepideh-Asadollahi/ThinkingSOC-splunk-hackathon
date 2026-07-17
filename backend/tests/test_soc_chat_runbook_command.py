"""Natural-language Chat → approved Runbook execution routing."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from services.soc_rag.models import SocChatMessage, SocChatRequest
from services.soc_rag.runbook_command import (
    RunbookChatCommandResult,
    RunbookExecutionIntent,
    detect_runbook_execution_intent,
    execute_runbook_chat_command,
)


@pytest.mark.parametrize(
    ("text", "sid", "language"),
    [
        (
            "Please run the approved Runbook for SID demo-runbook-target-20260716",
            "demo-runbook-target-20260716",
            "en",
        ),
        ("Can you execute the playbook for SID: alert-123?", "alert-123", "en"),
        (
            "Please run the approved runbook for SID scheduler__admin_search.",
            "scheduler__admin_search",
            "en",
        ),
    ],
)
def test_detect_runbook_execution_intent(text: str, sid: str, language: str) -> None:
    intent = detect_runbook_execution_intent(text)
    assert intent.detected is True
    assert intent.sid == sid
    assert intent.language == language


def test_runbook_command_understands_contextual_english_follow_up() -> None:
    intent = detect_runbook_execution_intent(
        "Execute it for SID alert-456",
        prior_messages=[{"role": "assistant", "content": "This approved Runbook is ready for guarded execution."}],
    )
    assert intent.detected is True
    assert intent.sid == "alert-456"


@pytest.mark.parametrize(
    "text",
    [
        "Don't run the runbook for SID alert-123",
        "Explain the Runbook for SID alert-123 without running it",
        "What investigation steps are in this Runbook?",
    ],
)
def test_runbook_command_does_not_execute_negation_or_questions(text: str) -> None:
    assert detect_runbook_execution_intent(text).detected is False


def test_runbook_command_requests_one_explicit_sid() -> None:
    missing = detect_runbook_execution_intent("Run the Runbook")
    multiple = detect_runbook_execution_intent(
        "Run the Runbook for SID alert-1 and SID alert-2"
    )
    assert missing.detected is True and missing.reason == "missing_sid"
    assert multiple.detected is True and multiple.reason == "multiple_sids"
    assert multiple.sid_candidates == ("alert-1", "alert-2")


@pytest.mark.asyncio
async def test_execute_command_resolves_sid_and_uses_guarded_runbook_service() -> None:
    settings = SimpleNamespace(tsoc_runbook_default_manual_minutes=30)
    intent = RunbookExecutionIntent(
        detected=True,
        sid="target-sid-2",
        sid_candidates=("target-sid-2",),
        language="en",
        reason="ready",
    )
    target = {
        "id": 202,
        "sid": "target-sid-2",
        "search_name": "Suspicious OAuth Replay",
        "tsoc_record_type": "soc_analysis",
        "payload": {},
    }
    draft = SimpleNamespace(
        runbook_id="rb-approved",
        source_record_id=101,
        title="Investigate OAuth replay",
        status="SOURCE_VERIFIED",
        applicable_search_name="Suspicious OAuth Replay",
        created_at="2026-07-16T10:00:00+00:00",
        revision=2,
        steps=[SimpleNamespace(), SimpleNamespace()],
    )
    item = SimpleNamespace(
        draft=draft,
        latest_approval=SimpleNamespace(decision="approve"),
        is_latest_for_source=True,
    )
    library = SimpleNamespace(
        groups=[SimpleNamespace(alert_name="Suspicious OAuth Replay", runbooks=[item])]
    )
    run_result = SimpleNamespace(
        status="REUSED",
        successful_step_count=2,
        total_evidence_rows=4,
        duration_ms=1250,
    )

    with (
        patch(
            "services.soc_rag.runbook_command.search_stored_events",
            new_callable=AsyncMock,
            return_value=[target],
        ) as search,
        patch(
            "services.soc_rag.runbook_command.list_runbook_library",
            new_callable=AsyncMock,
            return_value=library,
        ) as list_library,
        patch(
            "services.soc_rag.runbook_command.run_verified_runbook",
            new_callable=AsyncMock,
            return_value=run_result,
        ) as execute,
    ):
        result = await execute_runbook_chat_command(settings, intent, request_id="rid-test")

    search.assert_awaited_once_with(
        settings,
        job_sid="target-sid-2",
        record_type="soc_analysis",
        limit=100,
        order="desc",
    )
    list_library.assert_awaited_once_with(
        settings,
        search_name="Suspicious OAuth Replay",
    )
    body = execute.await_args.args[2]
    assert execute.await_args.args[:2] == (settings, 202)
    assert body.source_record_id == 101
    assert body.runbook_id == "rb-approved"
    assert body.estimated_manual_minutes == 30
    assert result.metadata["status"] == "REUSED"
    assert result.metadata["automatic_response_executed"] is False
    assert result.citations[0].sid == "target-sid-2"
    assert "read-only" in result.answer


@pytest.mark.asyncio
async def test_run_soc_chat_routes_command_before_rag_or_llm() -> None:
    from services.soc_rag.chat import run_soc_chat

    settings = SimpleNamespace()
    body = SocChatRequest(
        messages=[
            SocChatMessage(
                role="user",
                content="Run the approved Runbook for SID target-sid-2",
            )
        ],
        conversation_id="conv-runbook",
    )
    command_result = RunbookChatCommandResult(
        answer="Runbook completed safely.",
        metadata={"query_mode": "runbook_execute", "status": "REUSED"},
    )
    with (
        patch("services.soc_rag.chat.splunk_store_configured", return_value=True),
        patch(
            "services.soc_rag.chat._resolve_conversation_messages",
            new_callable=AsyncMock,
            return_value=(
                "conv-runbook",
                [{"role": "user", "content": body.messages[0].content}],
            ),
        ),
        patch(
            "services.soc_rag.chat.execute_runbook_chat_command",
            new_callable=AsyncMock,
            return_value=command_result,
        ) as execute,
        patch(
            "services.soc_rag.chat._persist_turn",
            new_callable=AsyncMock,
        ) as persist,
        patch(
            "services.soc_rag.chat.retrieve_rag_documents",
            new_callable=AsyncMock,
        ) as retrieve,
        patch(
            "services.soc_rag.chat.litellm_chat_completion",
            new_callable=AsyncMock,
        ) as llm,
    ):
        response = await run_soc_chat(settings, body, request_id="rid-chat")

    execute.assert_awaited_once()
    persist.assert_awaited_once()
    retrieve.assert_not_awaited()
    llm.assert_not_awaited()
    assert response.retrieval_backend == "runbook_executor"
    assert response.retrieval_meta["status"] == "REUSED"
