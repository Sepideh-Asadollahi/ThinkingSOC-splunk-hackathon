"""Compact ThinkingSOC Lite artifacts into safe, immediately queryable SOC Chat documents."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Optional

from .models import RagAlertDocument


_DOC_TYPES = {
    "verified_runbook_draft": "runbook_draft",
    "verified_runbook_approval": "runbook_approval",
    "verified_runbook_run": "runbook_run",
    "verified_runbook_shadow_run": "runbook_shadow_run",
    "verified_runbook_response_preview": "runbook_response_preview",
    "verified_runbook_response_decision": "runbook_response_decision",
    "verified_runbook_autopilot_session": "runbook_autopilot",
}


def _payload(value: Dict[str, Any]) -> Dict[str, Any]:
    nested = value.get("payload")
    return nested if isinstance(nested, dict) else value


def _text(value: Any, *, limit: int = 2000) -> str:
    result = str(value or "").strip()
    return result[:limit]


def _stable_doc_id(record_type: str, payload: Dict[str, Any]) -> str:
    identity = (
        payload.get("session_id")
        or payload.get("preview_id")
        or payload.get("shadow_run_id")
        or payload.get("runbook_id")
        or payload.get("source_record_id")
        or "unknown"
    )
    revision = payload.get("revision") or payload.get("created_at") or "latest"
    digest = hashlib.sha256(
        f"{record_type}:{identity}:{revision}".encode("utf-8")
    ).hexdigest()[:20]
    return f"{record_type}:{digest}"


def _draft_lines(payload: Dict[str, Any]) -> list[str]:
    lines = [
        f"Runbook title: {_text(payload.get('title'))}",
        f"Summary: {_text(payload.get('summary'))}",
        f"Runbook ID: {_text(payload.get('runbook_id'))}",
        f"Source record: {_text(payload.get('source_record_id'))}",
        f"Alert Name: {_text(payload.get('applicable_search_name'))}",
        f"Status: {_text(payload.get('status'))}",
        f"Revision: {_text(payload.get('revision'))}",
        f"Source verdict: {_text(payload.get('source_verdict'))}",
        f"Decision rule: {_text(payload.get('decision_rule'))}",
    ]
    for index, step in enumerate(payload.get("steps") or [], 1):
        if not isinstance(step, dict):
            continue
        lines.append(
            "Step {0}: {1}. Intent: {2}. Expected evidence: {3}. Stop condition: {4}.".format(
                index,
                _text(step.get("title"), limit=300),
                _text(step.get("intent")),
                _text(step.get("expected_evidence"), limit=1000),
                _text(step.get("stop_condition"), limit=1000),
            )
        )
    limitations = [_text(item, limit=500) for item in payload.get("limitations") or []]
    if limitations:
        lines.append("Limitations: " + "; ".join(limitations))
    lines.append(
        "Evidence metrics: parser-valid steps={0}, successful steps={1}, evidence rows={2}.".format(
            payload.get("parser_valid_step_count") or 0,
            payload.get("successful_step_count") or 0,
            payload.get("total_evidence_rows") or 0,
        )
    )
    return lines


def _preview_lines(payload: Dict[str, Any]) -> list[str]:
    lines = [
        f"Safe Response Preview for Runbook {_text(payload.get('runbook_id'))}.",
        f"Evidence basis: {_text(payload.get('evidence_basis'))}.",
        f"Decision summary: {_text(payload.get('decision_summary'))}.",
        "Execution supported: false. Every action requires human approval.",
    ]
    for action in payload.get("actions") or []:
        if not isinstance(action, dict):
            continue
        lines.append(
            "Preview action {0}: {1}; target {2}; risk {3}; rationale {4}; "
            "expected effect {5}; rollback {6}; mode PREVIEW_ONLY.".format(
                _text(action.get("action_type"), limit=100),
                _text(action.get("title"), limit=300),
                _text(action.get("target"), limit=500),
                _text(action.get("risk_level"), limit=50),
                _text(action.get("rationale"), limit=1000),
                _text(action.get("expected_effect"), limit=500),
                _text(action.get("rollback_plan"), limit=500),
            )
        )
    return lines


def _autopilot_lines(payload: Dict[str, Any]) -> list[str]:
    lines = [
        f"Runbook Autopilot session: {_text(payload.get('session_id'))}",
        f"Objective: {_text(payload.get('objective'))}",
        f"Mode: {_text(payload.get('mode'))}; status: {_text(payload.get('status'))}",
        "Agents: " + ", ".join(_text(v, limit=100) for v in payload.get("agents") or []),
        "Tools used: "
        + ", ".join(_text(v, limit=120) for v in payload.get("tools_used") or []),
        f"Runbook ID: {_text(payload.get('runbook_id'))}; Runbook status: {_text(payload.get('runbook_status'))}",
        f"Response preview ID: {_text(payload.get('response_preview_id'))}",
        f"Next recommended action: {_text(payload.get('next_recommended_action'))}",
        "Human approval required: true; automatic execution performed: false.",
    ]
    for event in payload.get("trace") or []:
        if not isinstance(event, dict):
            continue
        lines.append(
            "Trace {0}: agent={1}, kind={2}, status={3}, tool={4}, summary={5}, duration_ms={6}.".format(
                event.get("sequence") or "-",
                _text(event.get("agent"), limit=100),
                _text(event.get("kind"), limit=100),
                _text(event.get("status"), limit=100),
                _text(event.get("tool_name"), limit=150) or "-",
                _text(event.get("summary"), limit=700),
                event.get("duration_ms") or 0,
            )
        )
    return lines


def compact_runbook_artifact(
    record_type: str,
    value: Dict[str, Any],
) -> Optional[RagAlertDocument]:
    """Return a compact document without raw SPL results or alert payloads."""
    doc_type = _DOC_TYPES.get(record_type)
    if doc_type is None:
        return None
    payload = _payload(value)
    search_name = _text(
        value.get("search_name")
        or payload.get("applicable_search_name")
        or payload.get("search_name"),
        limit=500,
    ) or None

    if record_type == "verified_runbook_draft":
        lines = _draft_lines(payload)
        summary = "Runbook {0} — {1}".format(
            _text(payload.get("title"), limit=300),
            _text(payload.get("status"), limit=100),
        )
    elif record_type == "verified_runbook_response_preview":
        lines = _preview_lines(payload)
        summary = "Safe Response Preview — {0} action(s), execution disabled".format(
            len(payload.get("actions") or [])
        )
    elif record_type == "verified_runbook_autopilot_session":
        lines = _autopilot_lines(payload)
        summary = "Runbook Autopilot — {0}; {1}".format(
            _text(payload.get("status"), limit=100),
            _text(payload.get("next_recommended_action"), limit=300),
        )
    else:
        safe = {
            key: payload.get(key)
            for key in (
                "runbook_id",
                "source_record_id",
                "target_record_id",
                "preview_id",
                "decision",
                "status",
                "analyst",
                "note",
                "duration_ms",
                "estimated_minutes_saved",
                "projected_minutes_saved",
                "total_evidence_rows",
                "automatic_execution_performed",
                "created_at",
            )
            if payload.get(key) is not None
        }
        lines = [
            f"ThinkingSOC Lite artifact type: {doc_type}",
            json.dumps(safe, ensure_ascii=False, default=str),
        ]
        summary = "{0} for Runbook {1}".format(
            doc_type.replace("_", " ").title(),
            _text(payload.get("runbook_id"), limit=128),
        )

    essential = {
        key: payload.get(key)
        for key in (
            "runbook_id",
            "source_record_id",
            "target_record_id",
            "session_id",
            "preview_id",
            "status",
            "decision",
            "revision",
        )
        if payload.get(key) is not None
    }
    return RagAlertDocument(
        doc_type=doc_type,
        doc_id=_stable_doc_id(record_type, payload),
        sid=_text(value.get("sid"), limit=500) or None,
        search_name=search_name,
        row_index=int(value.get("row_index") or 0),
        essential=essential,
        summary_line=summary[:1000],
        chunk_text="\n".join(lines)[:20000],
        metadata={
            "source": "thinking_soc_lite",
            "record_type": record_type,
            "automatic_execution": False,
        },
    )
