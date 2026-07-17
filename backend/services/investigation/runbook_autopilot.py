"""Bounded multi-agent orchestration for ThinkingSOC Forge runbooks.

The Autopilot advances only reversible/read-only workflow stages. Approval,
production reuse, and response execution remain explicit analyst actions.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from config import Settings
from models.runbook import (
    RunbookAutopilotBody,
    RunbookAutopilotEvent,
    RunbookAutopilotSession,
    SafeResponsePreviewBody,
)
from services.investigation.investigation_workflow import (
    list_analyst_actions_for_record,
)
from services.investigation.verified_runbook import (
    VerifiedRunbookError,
    build_safe_response_preview,
    build_verified_runbook,
    get_verified_runbook_state,
    list_runbook_library,
)
from services.splunk_json_store import (
    get_stored_event_by_id,
    search_stored_events,
    splunk_store_configured,
    submit_hec_event,
)

RUNBOOK_AUTOPILOT_RECORD_TYPE = "verified_runbook_autopilot_session"

logger = logging.getLogger(__name__)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _payload(row: Dict[str, Any]) -> Dict[str, Any]:
    value = row.get("payload")
    return value if isinstance(value, dict) else {}


class _Trace:
    def __init__(self) -> None:
        self.events: List[RunbookAutopilotEvent] = []
        self.tools: List[str] = []
        self.agents: List[str] = []

    def add(
        self,
        agent: str,
        kind: str,
        status: str,
        summary: str,
        *,
        tool_name: Optional[str] = None,
        duration_ms: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        if agent not in self.agents:
            self.agents.append(agent)
        if tool_name and tool_name not in self.tools:
            self.tools.append(tool_name)
        self.events.append(
            RunbookAutopilotEvent(
                event_id=str(uuid4()),
                sequence=len(self.events) + 1,
                agent=agent,
                kind=kind,
                status=status,
                summary=summary,
                tool_name=tool_name,
                duration_ms=duration_ms,
                metadata=metadata or {},
                created_at=_utc_now(),
            )
        )


async def _persist_session(
    settings: Settings,
    *,
    source: Dict[str, Any],
    session: RunbookAutopilotSession,
) -> None:
    event = {
        "tsoc_record_type": RUNBOOK_AUTOPILOT_RECORD_TYPE,
        "sid": source.get("sid"),
        "search_name": source.get("search_name"),
        "row_index": source.get("row_index"),
        **session.model_dump(mode="json"),
    }
    persisted = await submit_hec_event(settings, event)
    if not persisted:
        raise VerifiedRunbookError(
            "Failed to persist Runbook Autopilot session.", status_code=502
        )
    from services.soc_rag.index_writer import schedule_runbook_artifact_index

    schedule_runbook_artifact_index(
        settings,
        record_type=RUNBOOK_AUTOPILOT_RECORD_TYPE,
        event=event,
    )


async def get_latest_runbook_autopilot_session(
    settings: Settings,
    source_record_id: int,
) -> Optional[RunbookAutopilotSession]:
    if not splunk_store_configured(settings):
        raise VerifiedRunbookError(
            "PostgreSQL store not configured; set TSOC_POSTGRES_DSN.",
            status_code=503,
        )
    rows = await search_stored_events(
        settings,
        record_type=RUNBOOK_AUTOPILOT_RECORD_TYPE,
        limit=settings.tsoc_runbook_artifact_scan_limit,
        order="desc",
    )
    for row in rows:
        payload = _payload(row)
        if payload.get("source_record_id") not in (
            source_record_id,
            str(source_record_id),
        ):
            continue
        try:
            return RunbookAutopilotSession.model_validate(payload)
        except Exception as exc:
            logger.warning(
                "runbook_autopilot invalid_session storage_record_id=%s error=%s",
                row.get("id"),
                exc,
            )
    return None


def _verification_transports(draft: Any) -> List[str]:
    transports: List[str] = []
    for item in getattr(draft, "source_results", []) or []:
        spl_results = getattr(item, "spl_results", None)
        transport = getattr(spl_results, "execution_transport", None)
        if transport and transport not in transports:
            transports.append(str(transport))
    return transports


async def run_runbook_autopilot(
    settings: Settings,
    source_record_id: int,
    body: RunbookAutopilotBody,
) -> RunbookAutopilotSession:
    """Run the bounded Forge orchestration and persist its complete audit trace."""
    if not getattr(settings, "tsoc_runbook_autopilot_enabled", True):
        raise VerifiedRunbookError("Runbook Autopilot is disabled.", status_code=503)
    if not splunk_store_configured(settings):
        raise VerifiedRunbookError(
            "PostgreSQL store not configured; set TSOC_POSTGRES_DSN.",
            status_code=503,
        )

    started = time.perf_counter()
    started_at = _utc_now()
    session_id = str(uuid4())
    trace = _Trace()
    trace.add(
        "SUPERVISOR",
        "AGENT_STARTED",
        "RUNNING",
        "Autopilot accepted the objective and opened a bounded workflow.",
        metadata={"mode": body.mode},
    )
    trace.add(
        "SUPERVISOR",
        "HANDOFF",
        "RUNNING",
        "Delegated source readiness and acknowledgment checks to Evidence Scout.",
        metadata={"to_agent": "EVIDENCE_SCOUT"},
    )

    tool_started = time.perf_counter()
    trace.add(
        "EVIDENCE_SCOUT",
        "TOOL_CALL",
        "RUNNING",
        "Loading the stored SOC analysis without exposing credentials.",
        tool_name="storage.get_record",
    )
    source = await get_stored_event_by_id(settings, source_record_id)
    if source is None:
        raise VerifiedRunbookError("Record not found", status_code=404)
    if str(source.get("tsoc_record_type") or "") != "soc_analysis":
        raise VerifiedRunbookError(
            "Runbook Autopilot requires a stored soc_analysis record."
        )
    trace.add(
        "EVIDENCE_SCOUT",
        "TOOL_RESULT",
        "SUCCEEDED",
        "Stored SOC analysis loaded.",
        tool_name="storage.get_record",
        duration_ms=round((time.perf_counter() - tool_started) * 1000),
        metadata={
            "source_record_id": source_record_id,
            "search_name": str(source.get("search_name") or ""),
        },
    )

    action_started = time.perf_counter()
    trace.add(
        "EVIDENCE_SCOUT",
        "TOOL_CALL",
        "RUNNING",
        "Checking the latest human analyst action.",
        tool_name="analyst_actions.list",
    )
    analyst_actions = await list_analyst_actions_for_record(settings, source_record_id)
    acknowledged = bool(analyst_actions and analyst_actions[0].get("action") == "acknowledge")
    trace.add(
        "EVIDENCE_SCOUT",
        "TOOL_RESULT",
        "SUCCEEDED" if acknowledged else "BLOCKED",
        "Source acknowledgment is present."
        if acknowledged
        else "Source acknowledgment is required before Autopilot may advance.",
        tool_name="analyst_actions.list",
        duration_ms=round((time.perf_counter() - action_started) * 1000),
        metadata={"acknowledged": acknowledged},
    )
    trace.add(
        "EVIDENCE_SCOUT",
        "HANDOFF",
        "SUCCEEDED",
        "Passed the bounded source metadata to Runbook Engineer.",
        metadata={"to_agent": "RUNBOOK_ENGINEER"},
    )

    state_started = time.perf_counter()
    trace.add(
        "RUNBOOK_ENGINEER",
        "TOOL_CALL",
        "RUNNING",
        "Loading the latest immutable Runbook state.",
        tool_name="runbook.state",
    )
    state = await get_verified_runbook_state(settings, source_record_id)
    draft = state.draft
    trace.add(
        "RUNBOOK_ENGINEER",
        "TOOL_RESULT",
        "SUCCEEDED",
        "Latest Runbook state loaded.",
        tool_name="runbook.state",
        duration_ms=round((time.perf_counter() - state_started) * 1000),
        metadata={
            "runbook_id": draft.runbook_id if draft else None,
            "runbook_status": draft.status if draft else None,
        },
    )

    library_started = time.perf_counter()
    trace.add(
        "RUNBOOK_ENGINEER",
        "TOOL_CALL",
        "RUNNING",
        "Searching the library by exact Alert Name.",
        tool_name="runbook.library.search",
    )
    library = await list_runbook_library(
        settings,
        search_name=str(source.get("search_name") or ""),
    )
    trace.add(
        "RUNBOOK_ENGINEER",
        "TOOL_RESULT",
        "SUCCEEDED",
        "Exact-name Runbook candidates evaluated.",
        tool_name="runbook.library.search",
        duration_ms=round((time.perf_counter() - library_started) * 1000),
        metadata={"matching_revisions": library.count},
    )
    trace.add(
        "RUNBOOK_ENGINEER",
        "HANDOFF",
        "SUCCEEDED",
        "Requested an explicit gate decision from Policy Guard.",
        metadata={"to_agent": "POLICY_GUARD"},
    )

    if not acknowledged:
        trace.add(
            "POLICY_GUARD",
            "POLICY_DECISION",
            "BLOCKED",
            "Autopilot stopped before generation because acknowledgment is missing.",
            metadata={"automatic_execution": False},
        )
        status = "BLOCKED"
        next_action = "Acknowledge the investigation, then run Autopilot again."
    elif body.mode == "ASSESS":
        trace.add(
            "POLICY_GUARD",
            "POLICY_DECISION",
            "SUCCEEDED",
            "Assessment mode permits observation only; no workflow mutation was requested.",
            metadata={"automatic_execution": False},
        )
        status = "COMPLETED"
        next_action = (
            "Run Autopilot in ADVANCE mode to compile or enrich the Runbook safely."
            if draft is None
            else "Review the current Runbook and its evidence state."
        )
    else:
        trace.add(
            "POLICY_GUARD",
            "POLICY_DECISION",
            "SUCCEEDED",
            "Read-only compile and evidence verification are allowed; approval and execution remain human-only.",
            metadata={"automatic_execution": False},
        )
        if draft is None:
            compile_started = time.perf_counter()
            trace.add(
                "RUNBOOK_ENGINEER",
                "TOOL_CALL",
                "RUNNING",
                "Compiling and read-only verifying a new immutable Runbook revision.",
                tool_name="runbook.compile_and_verify",
            )
            try:
                draft = await build_verified_runbook(settings, source_record_id)
                transports = _verification_transports(draft)
                trace.add(
                    "RUNBOOK_ENGINEER",
                    "TOOL_RESULT",
                    "SUCCEEDED" if draft.status != "FAILED" else "FAILED",
                    "Runbook compilation and verification finished.",
                    tool_name="runbook.compile_and_verify",
                    duration_ms=round((time.perf_counter() - compile_started) * 1000),
                    metadata={
                        "runbook_id": draft.runbook_id,
                        "runbook_status": draft.status,
                        "verification_transports": transports,
                        "mcp_preferred_rest_fallback": True,
                    },
                )
            except Exception as exc:
                trace.add(
                    "RUNBOOK_ENGINEER",
                    "TOOL_RESULT",
                    "FAILED",
                    "Runbook compilation could not complete.",
                    tool_name="runbook.compile_and_verify",
                    duration_ms=round((time.perf_counter() - compile_started) * 1000),
                    metadata={"error_type": type(exc).__name__, "error": str(exc)[:500]},
                )
                draft = None

        preview = state.latest_response_preview
        if (
            draft is not None
            and body.generate_response_preview
            and draft.status in {"PARSER_VALID", "SOURCE_VERIFIED"}
            and (preview is None or preview.runbook_id != draft.runbook_id)
        ):
            trace.add(
                "POLICY_GUARD",
                "HANDOFF",
                "SUCCEEDED",
                "Permitted Response Advisor to create a non-executable preview.",
                metadata={"to_agent": "RESPONSE_ADVISOR"},
            )
            preview_started = time.perf_counter()
            trace.add(
                "RESPONSE_ADVISOR",
                "TOOL_CALL",
                "RUNNING",
                "Generating high-level response options with an enforced allowlist.",
                tool_name="runbook.safe_response_preview",
            )
            try:
                preview = await build_safe_response_preview(
                    settings,
                    source_record_id,
                    SafeResponsePreviewBody(runbook_id=draft.runbook_id),
                )
                trace.add(
                    "RESPONSE_ADVISOR",
                    "TOOL_RESULT",
                    "SUCCEEDED",
                    "Preview-only response options are ready for analyst review.",
                    tool_name="runbook.safe_response_preview",
                    duration_ms=round((time.perf_counter() - preview_started) * 1000),
                    metadata={
                        "preview_id": preview.preview_id,
                        "action_count": len(preview.actions),
                        "execution_supported": preview.execution_supported,
                    },
                )
            except Exception as exc:
                trace.add(
                    "RESPONSE_ADVISOR",
                    "TOOL_RESULT",
                    "FAILED",
                    "Safe Response Preview generation failed without executing any action.",
                    tool_name="runbook.safe_response_preview",
                    duration_ms=round((time.perf_counter() - preview_started) * 1000),
                    metadata={"error_type": type(exc).__name__, "error": str(exc)[:500]},
                )
                preview = None
        elif preview is not None and draft is not None and preview.runbook_id == draft.runbook_id:
            trace.add(
                "RESPONSE_ADVISOR",
                "TOOL_RESULT",
                "SUCCEEDED",
                "Reused the latest non-executable Response Preview; no duplicate LLM call was made.",
                tool_name="runbook.safe_response_preview.cache",
                metadata={
                    "preview_id": preview.preview_id,
                    "execution_supported": preview.execution_supported,
                },
            )

        if draft is None:
            status = "FAILED"
            next_action = "Inspect the failed tool result, correct runtime dependencies, and retry Autopilot."
        elif draft.status == "SOURCE_VERIFIED":
            approved = bool(
                state.latest_approval
                and state.latest_approval.runbook_id == draft.runbook_id
                and state.latest_approval.decision == "approve"
            )
            status = "COMPLETED" if approved else "AWAITING_HUMAN_APPROVAL"
            next_action = (
                "Select an exact-name target for guided read-only reuse."
                if approved
                else "Review source evidence and approve or reject this Runbook revision."
            )
        elif draft.status == "PARSER_VALID":
            status = "AWAITING_HUMAN_APPROVAL"
            next_action = "Review evidence gaps and rebuild before Runbook approval."
        else:
            status = "BLOCKED" if draft.status == "DRAFT" else "FAILED"
            next_action = "Review the Runbook validation failure and rebuild the revision."

    preview_id = None
    if "preview" in locals() and preview is not None:
        preview_id = preview.preview_id
    trace.add(
        "POLICY_GUARD",
        "POLICY_DECISION",
        "SUCCEEDED" if status in {"COMPLETED", "AWAITING_HUMAN_APPROVAL"} else status,
        "Automatic production execution and containment remain disabled.",
        metadata={
            "human_approval_required": True,
            "automatic_execution_performed": False,
        },
    )
    trace.add(
        "SUPERVISOR",
        "AGENT_COMPLETED",
        "SUCCEEDED" if status in {"COMPLETED", "AWAITING_HUMAN_APPROVAL"} else status,
        "Autopilot completed its bounded work and returned control to the analyst.",
        metadata={"next_recommended_action": next_action},
    )

    completed_at = _utc_now()
    session = RunbookAutopilotSession(
        session_id=session_id,
        source_record_id=source_record_id,
        objective=body.objective,
        mode=body.mode,
        status=status,
        agents=trace.agents,
        tools_used=trace.tools,
        trace=trace.events,
        runbook_id=draft.runbook_id if draft else None,
        runbook_status=draft.status if draft else None,
        response_preview_id=preview_id,
        next_recommended_action=next_action,
        started_at=started_at,
        completed_at=completed_at,
        duration_ms=max(0, round((time.perf_counter() - started) * 1000)),
    )
    await _persist_session(settings, source=source, session=session)
    logger.info(
        "runbook_event=autopilot.completed session_id=%s source_record_id=%s "
        "status=%s agents=%d tools=%d duration_ms=%d automatic_execution=false",
        session.session_id,
        source_record_id,
        session.status,
        len(session.agents),
        len(session.tools_used),
        session.duration_ms,
    )
    return session
