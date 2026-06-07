"""Investigation timeline and analyst actions."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from config import Settings
from services.investigation.investigation_workflow import (
    ANALYST_ACTION_RECORD_TYPE,
    _filter_timeline_rows,
    _pick_recommended_step_from_payload,
    _row_to_timeline_step,
    _timeline_detail,
    build_investigation_timeline,
    list_analyst_actions_for_record,
    record_analyst_action,
)


def test_row_to_timeline_step_soc_analysis() -> None:
    row = {
        "id": 42,
        "tsoc_record_type": "soc_analysis",
        "created_at": "2026-05-20T10:00:00+00:00",
        "payload": {
            "analysis": {
                "judge": {"verdict": "suspicious", "priority": "high"},
                "triage": {"investigation_priority": "high", "triage_score": 88},
            }
        },
    }
    step = _row_to_timeline_step(row, highlight_record_id=42)
    assert step["title"] == "SOC analysis"
    assert step["is_current_record"] is True
    assert "suspicious" in (step.get("detail") or "")


def test_filter_timeline_excludes_internal_shards_and_other_rows() -> None:
    anchor = {"id": 10, "sid": "sid-abc", "row_index": 0, "tsoc_record_type": "soc_analysis"}
    rows = [
        {"id": 1, "sid": "sid-abc", "row_index": 0, "tsoc_record_type": "splunk_ingest"},
        {"id": 10, "sid": "sid-abc", "row_index": 0, "tsoc_record_type": "soc_analysis"},
        {"id": 2, "sid": "sid-abc", "row_index": 1, "tsoc_record_type": "soc_analysis"},
        {"id": 3, "sid": "sid-abc", "row_index": 0, "tsoc_record_type": "soc_investigation_judge"},
        {"id": 4, "sid": "sid-abc", "row_index": 0, "tsoc_record_type": "soc_analysis_audit"},
    ]
    out = _filter_timeline_rows(rows, anchor, 10)
    types = [r["tsoc_record_type"] for r in out]
    assert types == ["splunk_ingest", "soc_analysis"]
    assert out[1]["id"] == 10


def test_filter_timeline_dedupes_rerun_pipeline_steps() -> None:
    anchor = {
        "id": 582,
        "sid": "sid-abc",
        "row_index": 0,
        "tsoc_record_type": "soc_analysis",
        "created_at": "2026-05-30T12:31:44+00:00",
    }
    rows = [
        {"id": 1, "sid": "sid-abc", "row_index": 0, "tsoc_record_type": "splunk_ingest", "created_at": "2026-05-23T22:25:00+00:00"},
        {
            "id": 11,
            "sid": "sid-abc",
            "row_index": 0,
            "tsoc_record_type": "agentic_ops_analysis",
            "created_at": "2026-05-23T22:26:09+00:00",
            "payload": {"classification": {"track": "both", "recommended_pipeline": "dual"}},
        },
        {
            "id": 12,
            "sid": "sid-abc",
            "row_index": 0,
            "tsoc_record_type": "admin_org_gap_suggest",
            "created_at": "2026-05-23T22:25:49+00:00",
        },
        {
            "id": 21,
            "sid": "sid-abc",
            "row_index": 0,
            "tsoc_record_type": "agentic_ops_analysis",
            "created_at": "2026-05-29T07:36:50+00:00",
            "payload": {"classification": {"track": "both", "recommended_pipeline": "dual"}},
        },
        {
            "id": 22,
            "sid": "sid-abc",
            "row_index": 0,
            "tsoc_record_type": "admin_org_gap_suggest",
            "created_at": "2026-05-29T07:36:19+00:00",
        },
        {
            "id": 31,
            "sid": "sid-abc",
            "row_index": 0,
            "tsoc_record_type": "agentic_ops_analysis",
            "created_at": "2026-05-30T12:31:20+00:00",
            "payload": {"classification": {"track": "security", "recommended_pipeline": "security"}},
        },
        {
            "id": 32,
            "sid": "sid-abc",
            "row_index": 0,
            "tsoc_record_type": "admin_org_gap_suggest",
            "created_at": "2026-05-30T12:31:44+00:00",
        },
        {
            "id": 582,
            "sid": "sid-abc",
            "row_index": 0,
            "tsoc_record_type": "soc_analysis",
            "created_at": "2026-05-30T12:31:44+00:00",
            "payload": {"analysis": {"judge": {"verdict": "needs_investigation"}}},
        },
    ]
    out = _filter_timeline_rows(rows, anchor, 582)
    types = [r["tsoc_record_type"] for r in out]
    assert types.count("agentic_ops_analysis") == 1
    assert types.count("admin_org_gap_suggest") == 1
    assert types.count("soc_analysis") == 1
    assert out[-1]["id"] == 582
    kept_classification = next(r for r in out if r["tsoc_record_type"] == "agentic_ops_analysis")
    assert kept_classification["id"] == 31


def test_timeline_detail_marks_legacy_dual_classification() -> None:
    row = {
        "tsoc_record_type": "agentic_ops_analysis",
        "payload": {"classification": {"track": "both", "recommended_pipeline": "dual"}},
    }
    detail = _timeline_detail(row)
    assert detail is not None
    assert "legacy dual routing" in detail


@pytest.mark.asyncio
async def test_build_timeline_orders_pipeline_steps_by_rank(test_settings: Settings) -> None:
    anchor = {
        "id": 10,
        "sid": "sid-abc",
        "row_index": 0,
        "search_name": "Brute Force",
        "created_at": "2026-05-20T12:00:00+00:00",
        "tsoc_record_type": "soc_analysis",
        "payload": {},
    }
    rows = [
        {
            "id": 1,
            "sid": "sid-abc",
            "row_index": 0,
            "tsoc_record_type": "splunk_ingest",
            "created_at": "2026-05-20T10:00:00+00:00",
            "payload": {"normalized": {"host": "10.0.0.1"}},
        },
        {
            "id": 99,
            "sid": "sid-abc",
            "row_index": 0,
            "tsoc_record_type": "soc_investigation_hunter",
            "created_at": "2026-05-20T11:00:00+00:00",
            "payload": {},
        },
        {
            "id": 10,
            "sid": "sid-abc",
            "row_index": 0,
            "tsoc_record_type": "soc_analysis",
            "created_at": "2026-05-20T12:00:00+00:00",
            "payload": {"analysis": {"judge": {"verdict": "benign"}}},
        },
    ]

    with (
        patch(
            "services.investigation.investigation_workflow.get_stored_event_by_id",
            new_callable=AsyncMock,
            return_value=anchor,
        ),
        patch(
            "services.investigation.investigation_workflow.search_stored_events",
            new_callable=AsyncMock,
            return_value=rows,
        ),
        patch("services.investigation.investigation_workflow.splunk_store_configured", return_value=True),
    ):
        out = await build_investigation_timeline(test_settings, 10)

    assert out["found"] is True
    assert len(out["steps"]) == 2
    assert out["steps"][0]["record_type"] == "splunk_ingest"
    assert out["steps"][1]["record_type"] == "soc_analysis"


@pytest.mark.asyncio
async def test_record_analyst_action_rejects_invalid(test_settings: Settings) -> None:
    with pytest.raises(ValueError, match="acknowledge"):
        await record_analyst_action(test_settings, 1, action="invalid")


@pytest.mark.asyncio
async def test_record_analyst_action_persists(test_settings: Settings) -> None:
    anchor = {
        "id": 5,
        "sid": "sid-x",
        "search_name": "Test",
        "row_index": 0,
        "payload": {"analysis": {"judge": {"recommended_next_step": "Review logs"}}},
    }

    with (
        patch(
            "services.investigation.investigation_workflow.get_stored_event_by_id",
            new_callable=AsyncMock,
            return_value=anchor,
        ),
        patch("services.investigation.investigation_workflow.splunk_store_configured", return_value=True),
        patch(
            "services.investigation.investigation_workflow.submit_hec_event",
            new_callable=AsyncMock,
            return_value=True,
        ) as submit,
    ):
        result = await record_analyst_action(
            test_settings, 5, action="escalate", note="Tier 2"
        )

    assert result["ok"] is True
    submit.assert_awaited_once()
    event = submit.call_args[0][1]
    assert event["tsoc_record_type"] == ANALYST_ACTION_RECORD_TYPE
    assert event["action"] == "escalate"
    assert event["investigation_record_id"] == 5
    assert event["recommended_step_at_action"] == "Review logs"


def test_pick_recommended_step_from_judge_and_triage_report() -> None:
    payload = {
        "analysis": {
            "judge": {"recommended_next_step": "  Isolate host  "},
            "triage": {"report": {"recommended_action": "Escalate to tier 2"}},
        }
    }
    assert _pick_recommended_step_from_payload(payload) == "Isolate host"
    assert _pick_recommended_step_from_payload({"analysis": {}}) == ""


def test_timeline_detail_analyst_action() -> None:
    row = {
        "tsoc_record_type": ANALYST_ACTION_RECORD_TYPE,
        "payload": {"action": "escalate", "note": "Tier 2 queue"},
    }
    assert _timeline_detail(row) == "escalate — Tier 2 queue"


@pytest.mark.asyncio
async def test_build_timeline_not_found(test_settings: Settings) -> None:
    with patch(
        "services.investigation.investigation_workflow.get_stored_event_by_id",
        new_callable=AsyncMock,
        return_value=None,
    ):
        out = await build_investigation_timeline(test_settings, 999)
    assert out["found"] is False
    assert out["steps"] == []


@pytest.mark.asyncio
async def test_list_analyst_actions_filters_by_record_id(test_settings: Settings) -> None:
    anchor = {"id": 5, "sid": "sid-x"}
    rows = [
        {
            "id": 1,
            "created_at": "2026-05-22T09:00:00+00:00",
            "payload": {
                "investigation_record_id": 5,
                "action": "acknowledge",
                "note": "ok",
                "recommended_step_at_action": "Monitor",
            },
        },
        {
            "id": 2,
            "created_at": "2026-05-22T10:00:00+00:00",
            "payload": {
                "investigation_record_id": 99,
                "action": "escalate",
            },
        },
    ]
    with (
        patch(
            "services.investigation.investigation_workflow.get_stored_event_by_id",
            new_callable=AsyncMock,
            return_value=anchor,
        ),
        patch(
            "services.investigation.investigation_workflow.search_stored_events",
            new_callable=AsyncMock,
            return_value=rows,
        ),
        patch("services.investigation.investigation_workflow.splunk_store_configured", return_value=True),
    ):
        actions = await list_analyst_actions_for_record(test_settings, 5)

    assert len(actions) == 1
    assert actions[0]["action"] == "acknowledge"
    assert actions[0]["recommended_step"] == "Monitor"


@pytest.mark.asyncio
async def test_timeline_includes_analyst_action_step(test_settings: Settings) -> None:
    anchor = {
        "id": 10,
        "sid": "sid-abc",
        "search_name": "Alert",
        "tsoc_record_type": "soc_analysis",
        "payload": {},
    }
    rows = [
        anchor,
        {
            "id": 11,
            "sid": "sid-abc",
            "tsoc_record_type": ANALYST_ACTION_RECORD_TYPE,
            "created_at": "2026-05-20T13:00:00+00:00",
            "payload": {
                "action": "escalate",
                "note": "Handoff",
                "investigation_record_id": 10,
            },
        },
    ]
    with (
        patch(
            "services.investigation.investigation_workflow.get_stored_event_by_id",
            new_callable=AsyncMock,
            return_value=anchor,
        ),
        patch(
            "services.investigation.investigation_workflow.search_stored_events",
            new_callable=AsyncMock,
            return_value=rows,
        ),
        patch("services.investigation.investigation_workflow.splunk_store_configured", return_value=True),
    ):
        out = await build_investigation_timeline(test_settings, 10)

    analyst_steps = [s for s in out["steps"] if s["is_analyst_action"]]
    assert len(analyst_steps) == 1
    assert analyst_steps[0]["title"] == "Analyst decision"
    assert "escalate" in (analyst_steps[0].get("detail") or "")
