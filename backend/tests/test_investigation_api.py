"""Investigation timeline, analyst-actions, and verified-runbook HTTP API."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

from api.routes.investigation import post_verified_runbook
from config import Settings, get_settings
from main import app
from models.runbook import (
    RunbookAutopilotSession,
    RunbookApproval,
    RunbookCompatibleTarget,
    RunbookCompatibleTargets,
    RunbookEvaluationResponse,
    RunbookRun,
    RunbookShadowRun,
    RunbookStep,
    SafeResponseAction,
    SafeResponseDecision,
    SafeResponsePreview,
    VerifiedRunbookDraft,
    VerifiedRunbookState,
)
from services.investigation.verified_runbook import VerifiedRunbookError
from services.llm.litellm_service import LiteLLMProviderError

AUTH = {"Authorization": "Bearer expected-ingest-secret"}


@pytest.fixture
def client_investigation(test_settings_with_ingest_token: Settings):
    def _override() -> Settings:
        return test_settings_with_ingest_token.model_copy(
            update={"tsoc_postgres_dsn": "postgresql://test"}
        )

    app.dependency_overrides[get_settings] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


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
                intent="Determine whether the identity used unusual sources.",
                expected_evidence="Authentication events grouped by source.",
                stop_condition="Abstain when telemetry is missing.",
            )
        ],
        decision_rule="Escalate on corroboration; otherwise abstain.",
        status="SOURCE_VERIFIED",
        model="gpt-5.6-2026-07-01",
        compile_duration_ms=1000,
        created_at="2026-07-14T10:00:00+00:00",
    )


def _autopilot_session() -> RunbookAutopilotSession:
    return RunbookAutopilotSession(
        session_id="autopilot-1",
        source_record_id=10,
        objective="Assess and advance safely.",
        mode="ADVANCE",
        status="AWAITING_HUMAN_APPROVAL",
        agents=["SUPERVISOR", "POLICY_GUARD"],
        tools_used=["runbook.state"],
        runbook_id="rb-1",
        runbook_status="SOURCE_VERIFIED",
        next_recommended_action="Review and approve or reject.",
        started_at="2026-07-15T10:00:00+00:00",
        completed_at="2026-07-15T10:00:01+00:00",
        duration_ms=1000,
    )


def test_runbook_get_empty_state(client: TestClient) -> None:
    state = VerifiedRunbookState(record_id=10)
    with patch(
        "api.routes.investigation.get_verified_runbook_state",
        new_callable=AsyncMock,
        return_value=state,
    ):
        response = client.get("/api/v1/investigation/records/10/runbook")
    assert response.status_code == 200
    assert response.json()["draft"] is None


def test_runbook_autopilot_get_contract(client: TestClient) -> None:
    with patch(
        "api.routes.investigation.get_latest_runbook_autopilot_session",
        new_callable=AsyncMock,
        return_value=_autopilot_session(),
    ):
        response = client.get("/api/v1/investigation/records/10/runbook/autopilot")

    assert response.status_code == 200
    assert response.json()["latest_session"]["session_id"] == "autopilot-1"
    assert response.json()["latest_session"]["automatic_execution_performed"] is False


def test_runbook_autopilot_post_contract(client: TestClient) -> None:
    with patch(
        "api.routes.investigation.run_runbook_autopilot",
        new_callable=AsyncMock,
        return_value=_autopilot_session(),
    ) as service:
        response = client.post(
            "/api/v1/investigation/records/10/runbook/autopilot",
            json={"objective": "Assess and advance safely.", "mode": "ADVANCE"},
        )

    assert response.status_code == 200
    assert response.json()["status"] == "AWAITING_HUMAN_APPROVAL"
    assert response.json()["human_approval_required"] is True
    assert service.await_args.args[1] == 10


def test_runbook_build_success(client: TestClient) -> None:
    with patch(
        "api.routes.investigation.build_verified_runbook",
        new_callable=AsyncMock,
        return_value=_draft(),
    ):
        response = client.post("/api/v1/investigation/records/10/runbook")
    assert response.status_code == 200
    assert response.json()["status"] == "SOURCE_VERIFIED"


@pytest.mark.asyncio
async def test_runbook_create_if_missing_returns_existing_without_rebuild(
    test_settings: Settings,
) -> None:
    state = VerifiedRunbookState(record_id=10, draft=_draft())
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/investigation/records/10/runbook",
            "headers": [],
            "query_string": b"rebuild=false",
        }
    )
    with (
        patch(
            "api.routes.investigation.get_verified_runbook_state",
            new_callable=AsyncMock,
            return_value=state,
        ),
        patch(
            "api.routes.investigation.build_verified_runbook",
            new_callable=AsyncMock,
        ) as build,
    ):
        response = await post_verified_runbook(
            request,
            10,
            rebuild=False,
            settings=test_settings,
        )

    assert response["runbook_id"] == "rb-1"
    build.assert_not_awaited()


def test_runbook_build_maps_domain_conflict(client: TestClient) -> None:
    with patch(
        "api.routes.investigation.build_verified_runbook",
        new_callable=AsyncMock,
        side_effect=VerifiedRunbookError("Acknowledge first", status_code=409),
    ):
        response = client.post("/api/v1/investigation/records/10/runbook")
    assert response.status_code == 409
    assert response.json()["detail"] == "Acknowledge first"


@pytest.mark.parametrize(
    ("status_code", "message"),
    [(404, "Record not found"), (503, "PostgreSQL store not configured")],
)
def test_runbook_build_preserves_domain_status(
    client: TestClient, status_code: int, message: str
) -> None:
    with patch(
        "api.routes.investigation.build_verified_runbook",
        new_callable=AsyncMock,
        side_effect=VerifiedRunbookError(message, status_code=status_code),
    ):
        response = client.post("/api/v1/investigation/records/10/runbook")
    assert response.status_code == status_code


def test_runbook_build_maps_provider_timeout(client: TestClient) -> None:
    with patch(
        "api.routes.investigation.build_verified_runbook",
        new_callable=AsyncMock,
        side_effect=LiteLLMProviderError("provider timeout", kind="timeout"),
    ):
        response = client.post("/api/v1/investigation/records/10/runbook")
    assert response.status_code == 504


def test_runbook_settings_exposes_safe_runtime_status(client: TestClient) -> None:
    response = client.get("/api/v1/investigation/runbook-settings")
    assert response.status_code == 200
    assert response.json()["max_steps"] == 3
    assert response.json()["exact_search_name_required"] is True
    assert "password" not in response.text.lower()


def test_runbook_compatible_targets_contract(client: TestClient) -> None:
    targets = RunbookCompatibleTargets(
        source_record_id=10,
        search_name="Suspicious Login",
        count=1,
        results=[
            RunbookCompatibleTarget(
                record_id=20,
                sid="sid-20",
                search_name="Suspicious Login",
                summary="Compatible stored investigation",
                review_verdict="TRUE_POSITIVE",
            )
        ],
    )
    with patch(
        "api.routes.investigation.list_compatible_runbook_targets",
        new_callable=AsyncMock,
        return_value=targets,
    ) as service:
        response = client.get(
            "/api/v1/investigation/records/10/runbook/compatible-targets?limit=8"
        )

    assert response.status_code == 200
    assert response.json()["results"][0]["record_id"] == 20
    assert "payload" not in response.text
    assert service.await_args.kwargs["limit"] == 8


def test_runbook_approval_contract(client: TestClient) -> None:
    approval = RunbookApproval(
        runbook_id="rb-1",
        source_record_id=10,
        decision="approve",
        analyst="analyst",
        created_at="2026-07-14T10:00:00+00:00",
    )
    with patch(
        "api.routes.investigation.record_runbook_approval",
        new_callable=AsyncMock,
        return_value=approval,
    ) as service:
        response = client.post(
            "/api/v1/investigation/records/10/runbook/approval",
            json={"runbook_id": "rb-1", "decision": "approve", "note": "Reviewed"},
        )
    assert response.status_code == 200
    assert response.json()["decision"] == "approve"
    assert service.await_args.args[2].note == "Reviewed"


def test_runbook_run_contract(client: TestClient) -> None:
    run = RunbookRun(
        runbook_id="rb-1",
        source_record_id=10,
        target_record_id=20,
        status="REUSED",
        duration_ms=5000,
        estimated_manual_minutes=25,
        estimated_minutes_saved=24.917,
        created_at="2026-07-14T10:02:00+00:00",
    )
    with patch(
        "api.routes.investigation.run_verified_runbook",
        new_callable=AsyncMock,
        return_value=run,
    ) as service:
        response = client.post(
            "/api/v1/investigation/records/20/runbook-runs",
            json={
                "source_record_id": 10,
                "runbook_id": "rb-1",
                "estimated_manual_minutes": 25,
            },
        )
    assert response.status_code == 200
    assert response.json()["status"] == "REUSED"
    assert service.await_args.args[1] == 20


def test_runbook_run_maps_incompatible_target(client: TestClient) -> None:
    with patch(
        "api.routes.investigation.run_verified_runbook",
        new_callable=AsyncMock,
        side_effect=VerifiedRunbookError("Target search_name is not compatible"),
    ):
        response = client.post(
            "/api/v1/investigation/records/20/runbook-runs",
            json={"source_record_id": 10, "runbook_id": "rb-1"},
        )
    assert response.status_code == 409


def test_runbook_shadow_contract(client: TestClient) -> None:
    shadow = RunbookShadowRun(
        shadow_run_id="shadow-1",
        runbook_id="rb-1",
        source_record_id=10,
        target_record_id=20,
        source_sid="sid-10",
        target_sid="sid-20",
        search_name="Suspicious Login",
        status="NO_EVIDENCE",
        duration_ms=2500,
        estimated_manual_minutes=25,
        projected_minutes_saved=24.958,
        projected_labor_savings_usd=27.04,
        created_at="2026-07-14T10:03:00+00:00",
    )
    with patch(
        "api.routes.investigation.run_shadow_replay",
        new_callable=AsyncMock,
        return_value=shadow,
    ) as service:
        response = client.post(
            "/api/v1/investigation/records/20/runbook-shadow-runs",
            json={
                "source_record_id": 10,
                "runbook_id": "rb-1",
                "estimated_manual_minutes": 25,
            },
        )
    assert response.status_code == 200
    assert response.json()["shadow_run_id"] == "shadow-1"
    assert response.json()["status"] == "NO_EVIDENCE"
    assert service.await_args.args[1] == 20


def test_safe_response_preview_contract(client: TestClient) -> None:
    preview = SafeResponsePreview(
        preview_id="preview-1",
        runbook_id="rb-1",
        source_record_id=10,
        source_verdict="TRUE_POSITIVE",
        evidence_basis="SOURCE_EVIDENCE",
        actions=[
            SafeResponseAction(
                action_id="action-1",
                action_type="ISOLATE_ENDPOINT",
                title="Contain endpoint",
                target_type="endpoint",
                target="source-host",
                risk_level="high",
                rationale="Verified evidence supports containment review.",
                prerequisites=["Confirm business owner"],
                expected_effect="Stop external communication.",
                rollback_plan="Restore connectivity after eradication.",
                verification_steps=["Confirm communication has stopped"],
            )
        ],
        decision_summary="Review before manual handling.",
        model="openai/gpt-5.6",
        created_at="2026-07-14T10:03:00+00:00",
    )
    with patch(
        "api.routes.investigation.build_safe_response_preview",
        new_callable=AsyncMock,
        return_value=preview,
    ) as service:
        response = client.post(
            "/api/v1/investigation/records/10/runbook/response-preview",
            json={"runbook_id": "rb-1"},
        )
    assert response.status_code == 200
    assert response.json()["preview_id"] == "preview-1"
    assert response.json()["execution_supported"] is False
    assert response.json()["actions"][0]["execution_mode"] == "PREVIEW_ONLY"
    assert service.await_args.args[1] == 10


def test_safe_response_decision_contract(client: TestClient) -> None:
    decision = SafeResponseDecision(
        preview_id="preview-1",
        runbook_id="rb-1",
        source_record_id=10,
        decision="approve_for_manual_action",
        analyst="analyst",
        note="Evidence and rollback reviewed.",
        created_at="2026-07-14T10:04:00+00:00",
    )
    with patch(
        "api.routes.investigation.record_safe_response_decision",
        new_callable=AsyncMock,
        return_value=decision,
    ):
        response = client.post(
            "/api/v1/investigation/records/10/runbook/response-preview/decision",
            json={
                "preview_id": "preview-1",
                "decision": "approve_for_manual_action",
                "note": "Evidence and rollback reviewed.",
            },
        )
    assert response.status_code == 200
    assert response.json()["automatic_execution_performed"] is False
    assert response.json()["decision"] == "approve_for_manual_action"


def test_runbook_evaluation_contract(client: TestClient) -> None:
    evaluation = RunbookEvaluationResponse(
        generated_at="2026-07-14T10:04:00+00:00",
        revision_count=2,
        alert_count=1,
        latest_runbook_count=1,
        approved_runbook_count=0,
        production_run_count=0,
        shadow_run_count=1,
        source_verified_revision_count=0,
        parser_valid_revision_count=2,
        failed_revision_count=0,
        total_step_count=3,
        parser_valid_step_count=3,
        parser_valid_rate=100,
        shadow_evidence_run_count=0,
        evidence_coverage_rate=0,
        total_shadow_evidence_rows=0,
        total_execution_errors=0,
        average_compile_duration_ms=1200,
        average_shadow_duration_ms=2500,
        projected_minutes_saved=24.958,
        projected_labor_savings_usd=27.04,
        realized_minutes_saved=0,
        total_prompt_tokens=1000,
        total_completion_tokens=500,
        estimated_compile_llm_cost_usd=0,
        analyst_hourly_cost_usd=65,
        shadow_status_breakdown={"EVIDENCE_FOUND": 0, "NO_EVIDENCE": 1, "FAILED": 0},
    )
    with patch(
        "api.routes.investigation.get_runbook_evaluation",
        new_callable=AsyncMock,
        return_value=evaluation,
    ):
        response = client.get("/api/v1/investigation/runbook-evaluations")
    assert response.status_code == 200
    assert response.json()["parser_valid_rate"] == 100
    assert response.json()["shadow_run_count"] == 1


def test_timeline_503_without_postgres(client_with_token: TestClient) -> None:
    r = client_with_token.get(
        "/api/v1/investigation/records/1/timeline",
        headers=AUTH,
    )
    assert r.status_code == 503


def test_timeline_404_when_record_missing(client_investigation: TestClient) -> None:
    with patch(
        "api.routes.investigation.build_investigation_timeline",
        new_callable=AsyncMock,
        return_value={"record_id": 99, "found": False, "steps": []},
    ):
        r = client_investigation.get(
            "/api/v1/investigation/records/99/timeline",
            headers=AUTH,
        )
    assert r.status_code == 404


def test_timeline_ok(client_investigation: TestClient) -> None:
    payload = {
        "record_id": 10,
        "found": True,
        "sid": "sid-1",
        "search_name": "Brute Force",
        "steps": [
            {
                "record_id": 1,
                "record_type": "splunk_ingest",
                "title": "Splunk ingest",
                "description": "Alert received",
                "detail": None,
                "created_at": "2026-05-20T10:00:00+00:00",
                "is_current_record": False,
                "is_analyst_action": False,
            },
            {
                "record_id": 10,
                "record_type": "soc_analysis",
                "title": "SOC analysis",
                "description": "Pipeline completed",
                "detail": "Verdict suspicious",
                "created_at": "2026-05-20T12:00:00+00:00",
                "is_current_record": True,
                "is_analyst_action": False,
            },
        ],
    }
    with patch(
        "api.routes.investigation.build_investigation_timeline",
        new_callable=AsyncMock,
        return_value=payload,
    ):
        r = client_investigation.get(
            "/api/v1/investigation/records/10/timeline",
            headers=AUTH,
        )
    assert r.status_code == 200
    body = r.json()
    assert body["sid"] == "sid-1"
    assert len(body["steps"]) == 2
    assert body["steps"][0]["record_type"] == "splunk_ingest"


def test_analyst_actions_get_empty(client_investigation: TestClient) -> None:
    with patch(
        "api.routes.investigation.list_analyst_actions_for_record",
        new_callable=AsyncMock,
        return_value=[],
    ):
        r = client_investigation.get(
            "/api/v1/investigation/records/5/analyst-actions",
            headers=AUTH,
        )
    assert r.status_code == 200
    assert r.json()["count"] == 0
    assert r.json()["results"] == []


def test_analyst_actions_post_acknowledge(client_investigation: TestClient) -> None:
    saved = {
        "ok": True,
        "postgres_configured": True,
        "event": {"action": "acknowledge"},
        "created_at": "2026-05-22T10:00:00+00:00",
    }
    listed = [
        {
            "id": 100,
            "created_at": "2026-05-22T10:00:00+00:00",
            "action": "acknowledge",
            "note": "Reviewed",
            "recommended_step": "Monitor",
            "investigation_record_id": 5,
        }
    ]
    with (
        patch(
            "api.routes.investigation.record_analyst_action",
            new_callable=AsyncMock,
            return_value=saved,
        ),
        patch(
            "api.routes.investigation.list_analyst_actions_for_record",
            new_callable=AsyncMock,
            return_value=listed,
        ),
    ):
        r = client_investigation.post(
            "/api/v1/investigation/records/5/analyst-actions",
            headers=AUTH,
            json={"action": "acknowledge", "note": "Reviewed"},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["latest"]["action"] == "acknowledge"
    assert body["results"][0]["note"] == "Reviewed"


def test_analyst_actions_post_404(client_investigation: TestClient) -> None:
    with patch(
        "api.routes.investigation.record_analyst_action",
        new_callable=AsyncMock,
        side_effect=LookupError("Record not found"),
    ):
        r = client_investigation.post(
            "/api/v1/investigation/records/404/analyst-actions",
            headers=AUTH,
            json={"action": "escalate"},
        )
    assert r.status_code == 404


def test_analyst_actions_post_400_invalid_action(client_investigation: TestClient) -> None:
    r = client_investigation.post(
        "/api/v1/investigation/records/5/analyst-actions",
        headers=AUTH,
        json={"action": "block_ip"},
    )
    assert r.status_code == 422


def test_analyst_actions_post_502_when_persist_fails(client_investigation: TestClient) -> None:
    with patch(
        "api.routes.investigation.record_analyst_action",
        new_callable=AsyncMock,
        return_value={"ok": False, "postgres_configured": True},
    ):
        r = client_investigation.post(
            "/api/v1/investigation/records/5/analyst-actions",
            headers=AUTH,
            json={"action": "escalate"},
        )
    assert r.status_code == 502
