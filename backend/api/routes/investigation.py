"""Investigation timeline and analyst human-in-the-loop actions."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from api.deps import check_ingest_bearer
from api.http_rid import http_rid
from config import Settings, get_settings
from models.runbook import (
    RunbookAutopilotBody,
    RunbookApprovalBody,
    RunbookImportBody,
    RunbookRevisionBody,
    RunbookRunBody,
    RunbookShadowBody,
    SafeResponseDecisionBody,
    SafeResponsePreviewBody,
)
from services.investigation.runbook_autopilot import (
    get_latest_runbook_autopilot_session,
    run_runbook_autopilot,
)
from services.investigation.investigation_workflow import (
    build_investigation_timeline,
    list_analyst_actions_for_record,
    record_analyst_action,
)
from services.investigation.verified_runbook import (
    VerifiedRunbookError,
    build_safe_response_preview,
    build_verified_runbook,
    get_runbook_runtime_status,
    get_runbook_evaluation,
    get_verified_runbook_state,
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
from services.llm.litellm_service import (
    LiteLLMNotConfiguredError,
    LiteLLMProviderError,
    provider_error_http_status,
)
from services.splunk_json_store import splunk_store_configured

logger = logging.getLogger(__name__)
router = APIRouter()
_runbook_compile_locks: Dict[int, asyncio.Lock] = {}


def _runbook_error_needs_trace(exc: Exception) -> bool:
    return not isinstance(
        exc,
        (VerifiedRunbookError, LiteLLMNotConfiguredError, LiteLLMProviderError),
    )


class AnalystActionBody(BaseModel):
    action: Literal["acknowledge", "escalate"]
    note: Optional[str] = Field(None, max_length=2000)
    analyst: Optional[str] = Field(None, max_length=128)


@router.get(
    "/investigation/runbook-settings",
    dependencies=[Depends(check_ingest_bearer)],
)
async def get_verified_runbook_settings(
    settings: Settings = Depends(get_settings),
) -> Dict[str, Any]:
    """Expose non-secret Forge policy and runtime readiness to the UI."""
    return get_runbook_runtime_status(settings).model_dump(mode="json")


def _raise_runbook_http(exc: Exception) -> None:
    if isinstance(exc, VerifiedRunbookError):
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    if isinstance(exc, LiteLLMNotConfiguredError):
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if isinstance(exc, LiteLLMProviderError):
        raise HTTPException(
            status_code=provider_error_http_status(exc),
            detail=str(exc),
        ) from exc
    raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get(
    "/investigation/runbooks",
    dependencies=[Depends(check_ingest_bearer)],
)
async def get_runbook_library(
    request: Request,
    search_name: Optional[str] = Query(default=None, max_length=500),
    settings: Settings = Depends(get_settings),
) -> Dict[str, Any]:
    """List every stored runbook grouped by exact Alert Name."""
    try:
        library = await list_runbook_library(settings, search_name=search_name)
    except Exception as exc:
        logger.warning("api GET runbook-library rid=%s err=%s", http_rid(request), exc)
        _raise_runbook_http(exc)
    return library.model_dump(mode="json")


@router.get(
    "/investigation/runbook-evaluations",
    dependencies=[Depends(check_ingest_bearer)],
)
async def get_runbook_evaluations(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> Dict[str, Any]:
    """Return measured quality, evidence, latency, and economic metrics."""
    try:
        evaluation = await get_runbook_evaluation(settings)
    except Exception as exc:
        logger.warning(
            "runbook_event=api.evaluation_failed rid=%s error_type=%s err=%s",
            http_rid(request),
            type(exc).__name__,
            exc,
            exc_info=_runbook_error_needs_trace(exc),
        )
        _raise_runbook_http(exc)
    return evaluation.model_dump(mode="json")


@router.get(
    "/investigation/runbooks/export",
    dependencies=[Depends(check_ingest_bearer)],
)
async def get_runbook_export(
    request: Request,
    runbook_id: Optional[str] = Query(default=None, max_length=128),
    search_name: Optional[str] = Query(default=None, max_length=500),
    settings: Settings = Depends(get_settings),
) -> Dict[str, Any]:
    """Export portable intent-only JSON without evidence or approval state."""
    try:
        document = await export_runbooks(
            settings, runbook_id=runbook_id, search_name=search_name
        )
    except Exception as exc:
        logger.warning("api GET runbook-export rid=%s err=%s", http_rid(request), exc)
        _raise_runbook_http(exc)
    return document.model_dump(mode="json")


@router.post(
    "/investigation/runbooks/import",
    dependencies=[Depends(check_ingest_bearer)],
)
async def post_runbook_import(
    request: Request,
    body: RunbookImportBody,
    settings: Settings = Depends(get_settings),
) -> Dict[str, Any]:
    """Import v1 portable JSON as inert drafts or verified local artifacts."""
    started = time.perf_counter()
    logger.info(
        "runbook_event=api.import_requested rid=%s import_count=%d "
        "source_record_id=%s verify_on_source=%s",
        http_rid(request),
        len(body.document.runbooks),
        body.source_record_id,
        body.verify_on_source,
    )
    try:
        result = await import_runbooks(settings, body)
    except Exception as exc:
        logger.warning(
            "runbook_event=api.import_failed rid=%s error_type=%s err=%s",
            http_rid(request),
            type(exc).__name__,
            exc,
            exc_info=_runbook_error_needs_trace(exc),
        )
        _raise_runbook_http(exc)
    logger.info(
        "runbook_event=api.import_completed rid=%s imported_count=%d duration_ms=%d",
        http_rid(request),
        result.imported_count,
        max(0, round((time.perf_counter() - started) * 1000)),
    )
    return result.model_dump(mode="json")


@router.patch(
    "/investigation/runbooks/{runbook_id}",
    dependencies=[Depends(check_ingest_bearer)],
)
async def patch_runbook_revision(
    request: Request,
    runbook_id: str,
    body: RunbookRevisionBody,
    settings: Settings = Depends(get_settings),
) -> Dict[str, Any]:
    """Save an analyst edit as a new immutable revision."""
    started = time.perf_counter()
    logger.info(
        "runbook_event=api.revision_requested rid=%s parent_runbook_id=%s "
        "verify_on_source=%s step_count=%d",
        http_rid(request),
        runbook_id,
        body.verify_on_source,
        len(body.steps),
    )
    try:
        draft = await revise_runbook(settings, runbook_id, body)
    except Exception as exc:
        logger.warning(
            "runbook_event=api.revision_failed rid=%s parent_runbook_id=%s error_type=%s err=%s",
            http_rid(request),
            runbook_id,
            type(exc).__name__,
            exc,
            exc_info=_runbook_error_needs_trace(exc),
        )
        _raise_runbook_http(exc)
    logger.info(
        "runbook_event=api.revision_completed rid=%s parent_runbook_id=%s "
        "runbook_id=%s status=%s duration_ms=%d",
        http_rid(request),
        runbook_id,
        draft.runbook_id,
        draft.status,
        max(0, round((time.perf_counter() - started) * 1000)),
    )
    return draft.model_dump(mode="json")


@router.get(
    "/investigation/records/{record_id}/timeline",
    dependencies=[Depends(check_ingest_bearer)],
)
async def get_investigation_timeline(
    request: Request,
    record_id: int,
    settings: Settings = Depends(get_settings),
) -> Dict[str, Any]:
    """Chronological steps for the alert tied to a storage record (by sid)."""
    if not splunk_store_configured(settings):
        raise HTTPException(
            status_code=503,
            detail="PostgreSQL store not configured; set TSOC_POSTGRES_DSN.",
        )
    try:
        data = await build_investigation_timeline(settings, record_id)
    except Exception as e:
        logger.warning(
            "api GET investigation timeline record_id=%s rid=%s err=%s",
            record_id,
            http_rid(request),
            e,
            exc_info=True,
        )
        raise HTTPException(status_code=502, detail=str(e)) from e
    if not data.get("found"):
        raise HTTPException(status_code=404, detail="Record not found")
    return data


@router.get(
    "/investigation/records/{record_id}/analyst-actions",
    dependencies=[Depends(check_ingest_bearer)],
)
async def get_investigation_analyst_actions(
    request: Request,
    record_id: int,
    settings: Settings = Depends(get_settings),
) -> Dict[str, Any]:
    """Latest analyst acknowledge/escalate entries for this investigation record."""
    if not splunk_store_configured(settings):
        raise HTTPException(
            status_code=503,
            detail="PostgreSQL store not configured; set TSOC_POSTGRES_DSN.",
        )
    actions = await list_analyst_actions_for_record(settings, record_id)
    return {
        "record_id": record_id,
        "count": len(actions),
        "results": actions,
    }


@router.post(
    "/investigation/records/{record_id}/analyst-actions",
    dependencies=[Depends(check_ingest_bearer)],
)
async def post_investigation_analyst_action(
    request: Request,
    record_id: int,
    body: AnalystActionBody,
    settings: Settings = Depends(get_settings),
) -> Dict[str, Any]:
    """Record analyst acknowledge or escalate (human gate; no firewall execution)."""
    if not splunk_store_configured(settings):
        raise HTTPException(
            status_code=503,
            detail="PostgreSQL store not configured; set TSOC_POSTGRES_DSN.",
        )
    try:
        result = await record_analyst_action(
            settings,
            record_id,
            action=body.action,
            note=body.note,
            analyst=body.analyst,
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="Record not found") from None
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.warning(
            "api POST analyst-action record_id=%s rid=%s err=%s",
            record_id,
            http_rid(request),
            e,
            exc_info=True,
        )
        raise HTTPException(status_code=502, detail=str(e)) from e

    if not result.get("ok"):
        raise HTTPException(status_code=502, detail="Failed to persist analyst action")

    logger.info(
        "api POST analyst-action record_id=%s action=%s rid=%s",
        record_id,
        body.action,
        http_rid(request),
    )
    actions = await list_analyst_actions_for_record(settings, record_id)
    return {
        "record_id": record_id,
        "saved": result,
        "latest": actions[0] if actions else None,
        "results": actions,
    }


@router.post(
    "/investigation/records/{record_id}/runbook",
    dependencies=[Depends(check_ingest_bearer)],
)
async def post_verified_runbook(
    request: Request,
    record_id: int,
    rebuild: bool = Query(True),
    settings: Settings = Depends(get_settings),
) -> Dict[str, Any]:
    """Compile a revision, or atomically create one only when none exists."""
    started = time.perf_counter()
    logger.info(
        "runbook_event=api.compile_requested rid=%s source_record_id=%s rebuild=%s",
        http_rid(request),
        record_id,
        rebuild,
    )
    try:
        lock = _runbook_compile_locks.setdefault(record_id, asyncio.Lock())
        async with lock:
            if not rebuild:
                existing = await get_verified_runbook_state(settings, record_id)
                if existing.draft is not None:
                    logger.info(
                        "runbook_event=api.compile_skipped_existing rid=%s "
                        "source_record_id=%s runbook_id=%s revision=%s",
                        http_rid(request),
                        record_id,
                        existing.draft.runbook_id,
                        existing.draft.revision,
                    )
                    return existing.draft.model_dump(mode="json")
            draft = await build_verified_runbook(settings, record_id)
    except Exception as exc:
        logger.warning(
            "runbook_event=api.compile_failed rid=%s source_record_id=%s error_type=%s err=%s",
            http_rid(request),
            record_id,
            type(exc).__name__,
            exc,
            exc_info=_runbook_error_needs_trace(exc),
        )
        _raise_runbook_http(exc)
    logger.info(
        "runbook_event=api.compile_completed rid=%s source_record_id=%s "
        "runbook_id=%s status=%s duration_ms=%d",
        http_rid(request),
        record_id,
        draft.runbook_id,
        draft.status,
        max(0, round((time.perf_counter() - started) * 1000)),
    )
    return draft.model_dump(mode="json")


@router.get(
    "/investigation/records/{record_id}/runbook",
    dependencies=[Depends(check_ingest_bearer)],
)
async def get_verified_runbook(
    request: Request,
    record_id: int,
    settings: Settings = Depends(get_settings),
) -> Dict[str, Any]:
    """Return the latest draft, its decision, and its latest target run."""
    try:
        state = await get_verified_runbook_state(settings, record_id)
    except Exception as exc:
        logger.warning(
            "api GET verified-runbook record_id=%s rid=%s err=%s",
            record_id,
            http_rid(request),
            exc,
            exc_info=True,
        )
        _raise_runbook_http(exc)
    return state.model_dump(mode="json")


@router.get(
    "/investigation/records/{record_id}/runbook/autopilot",
    dependencies=[Depends(check_ingest_bearer)],
)
async def get_runbook_autopilot(
    request: Request,
    record_id: int,
    settings: Settings = Depends(get_settings),
) -> Dict[str, Any]:
    """Return the latest durable agent/tool trace for this investigation."""
    try:
        session = await get_latest_runbook_autopilot_session(settings, record_id)
    except Exception as exc:
        logger.warning(
            "runbook_event=api.autopilot_get_failed rid=%s source_record_id=%s err=%s",
            http_rid(request),
            record_id,
            exc,
            exc_info=_runbook_error_needs_trace(exc),
        )
        _raise_runbook_http(exc)
    return {"record_id": record_id, "latest_session": session.model_dump(mode="json") if session else None}


@router.post(
    "/investigation/records/{record_id}/runbook/autopilot",
    dependencies=[Depends(check_ingest_bearer)],
)
async def post_runbook_autopilot(
    request: Request,
    record_id: int,
    body: RunbookAutopilotBody,
    settings: Settings = Depends(get_settings),
) -> Dict[str, Any]:
    """Run bounded agent collaboration without auto-approval or response execution."""
    started = time.perf_counter()
    logger.info(
        "runbook_event=api.autopilot_requested rid=%s source_record_id=%s mode=%s",
        http_rid(request),
        record_id,
        body.mode,
    )
    try:
        session = await run_runbook_autopilot(settings, record_id, body)
    except Exception as exc:
        logger.warning(
            "runbook_event=api.autopilot_failed rid=%s source_record_id=%s "
            "error_type=%s err=%s",
            http_rid(request),
            record_id,
            type(exc).__name__,
            exc,
            exc_info=_runbook_error_needs_trace(exc),
        )
        _raise_runbook_http(exc)
    logger.info(
        "runbook_event=api.autopilot_completed rid=%s source_record_id=%s "
        "session_id=%s status=%s agents=%d tools=%d duration_ms=%d",
        http_rid(request),
        record_id,
        session.session_id,
        session.status,
        len(session.agents),
        len(session.tools_used),
        max(0, round((time.perf_counter() - started) * 1000)),
    )
    return session.model_dump(mode="json")


@router.get(
    "/investigation/records/{record_id}/runbook/compatible-targets",
    dependencies=[Depends(check_ingest_bearer)],
)
async def get_verified_runbook_compatible_targets(
    request: Request,
    record_id: int,
    limit: int = Query(12, ge=1, le=50),
    settings: Settings = Depends(get_settings),
) -> Dict[str, Any]:
    """List minimal exact-search-name candidates for guided reuse."""
    try:
        targets = await list_compatible_runbook_targets(
            settings,
            record_id,
            limit=limit,
        )
    except Exception as exc:
        logger.warning(
            "api GET runbook-compatible-targets record_id=%s rid=%s err=%s",
            record_id,
            http_rid(request),
            exc,
            exc_info=True,
        )
        _raise_runbook_http(exc)
    return targets.model_dump(mode="json")


@router.post(
    "/investigation/records/{record_id}/runbook/approval",
    dependencies=[Depends(check_ingest_bearer)],
)
async def post_verified_runbook_approval(
    request: Request,
    record_id: int,
    body: RunbookApprovalBody,
    settings: Settings = Depends(get_settings),
) -> Dict[str, Any]:
    """Record an explicit human approval or rejection for the latest draft."""
    started = time.perf_counter()
    logger.info(
        "runbook_event=api.approval_requested rid=%s source_record_id=%s runbook_id=%s decision=%s",
        http_rid(request),
        record_id,
        body.runbook_id,
        body.decision,
    )
    try:
        approval = await record_runbook_approval(settings, record_id, body)
    except Exception as exc:
        logger.warning(
            "runbook_event=api.approval_failed rid=%s source_record_id=%s "
            "runbook_id=%s error_type=%s err=%s",
            http_rid(request),
            record_id,
            body.runbook_id,
            type(exc).__name__,
            exc,
            exc_info=_runbook_error_needs_trace(exc),
        )
        _raise_runbook_http(exc)
    logger.info(
        "runbook_event=api.approval_completed rid=%s source_record_id=%s "
        "runbook_id=%s decision=%s duration_ms=%d",
        http_rid(request),
        record_id,
        approval.runbook_id,
        approval.decision,
        max(0, round((time.perf_counter() - started) * 1000)),
    )
    return approval.model_dump(mode="json")


@router.post(
    "/investigation/records/{record_id}/runbook/response-preview",
    dependencies=[Depends(check_ingest_bearer)],
)
async def post_safe_response_preview(
    request: Request,
    record_id: int,
    body: SafeResponsePreviewBody,
    settings: Settings = Depends(get_settings),
) -> Dict[str, Any]:
    """Generate an allowlisted, non-executable containment recommendation."""
    started = time.perf_counter()
    logger.info(
        "runbook_event=api.response_preview_requested rid=%s source_record_id=%s runbook_id=%s",
        http_rid(request),
        record_id,
        body.runbook_id,
    )
    try:
        preview = await build_safe_response_preview(settings, record_id, body)
    except Exception as exc:
        logger.warning(
            "runbook_event=api.response_preview_failed rid=%s source_record_id=%s "
            "runbook_id=%s error_type=%s err=%s",
            http_rid(request),
            record_id,
            body.runbook_id,
            type(exc).__name__,
            exc,
            exc_info=_runbook_error_needs_trace(exc),
        )
        _raise_runbook_http(exc)
    logger.info(
        "runbook_event=api.response_preview_completed rid=%s source_record_id=%s "
        "runbook_id=%s preview_id=%s action_count=%s duration_ms=%d",
        http_rid(request),
        record_id,
        preview.runbook_id,
        preview.preview_id,
        len(preview.actions),
        max(0, round((time.perf_counter() - started) * 1000)),
    )
    return preview.model_dump(mode="json")


@router.post(
    "/investigation/records/{record_id}/runbook/response-preview/decision",
    dependencies=[Depends(check_ingest_bearer)],
)
async def post_safe_response_decision(
    request: Request,
    record_id: int,
    body: SafeResponseDecisionBody,
    settings: Settings = Depends(get_settings),
) -> Dict[str, Any]:
    """Record human review for manual handling; no response action is executed."""
    started = time.perf_counter()
    logger.info(
        "runbook_event=api.response_decision_requested rid=%s source_record_id=%s "
        "preview_id=%s decision=%s",
        http_rid(request),
        record_id,
        body.preview_id,
        body.decision,
    )
    try:
        decision = await record_safe_response_decision(settings, record_id, body)
    except Exception as exc:
        logger.warning(
            "runbook_event=api.response_decision_failed rid=%s source_record_id=%s "
            "preview_id=%s error_type=%s err=%s",
            http_rid(request),
            record_id,
            body.preview_id,
            type(exc).__name__,
            exc,
            exc_info=_runbook_error_needs_trace(exc),
        )
        _raise_runbook_http(exc)
    logger.info(
        "runbook_event=api.response_decision_completed rid=%s source_record_id=%s "
        "preview_id=%s decision=%s automatic_execution_performed=%s duration_ms=%d",
        http_rid(request),
        record_id,
        decision.preview_id,
        decision.decision,
        decision.automatic_execution_performed,
        max(0, round((time.perf_counter() - started) * 1000)),
    )
    return decision.model_dump(mode="json")


@router.post(
    "/investigation/records/{target_record_id}/runbook-runs",
    dependencies=[Depends(check_ingest_bearer)],
)
async def post_verified_runbook_run(
    request: Request,
    target_record_id: int,
    body: RunbookRunBody,
    settings: Settings = Depends(get_settings),
) -> Dict[str, Any]:
    """Regenerate and execute an approved runbook on one compatible target."""
    started = time.perf_counter()
    logger.info(
        "runbook_event=api.reuse_requested rid=%s source_record_id=%s "
        "target_record_id=%s runbook_id=%s",
        http_rid(request),
        body.source_record_id,
        target_record_id,
        body.runbook_id,
    )
    try:
        run = await run_verified_runbook(settings, target_record_id, body)
    except Exception as exc:
        logger.warning(
            "runbook_event=api.reuse_failed rid=%s source_record_id=%s "
            "target_record_id=%s runbook_id=%s error_type=%s err=%s",
            http_rid(request),
            body.source_record_id,
            target_record_id,
            body.runbook_id,
            type(exc).__name__,
            exc,
            exc_info=_runbook_error_needs_trace(exc),
        )
        _raise_runbook_http(exc)
    logger.info(
        "runbook_event=api.reuse_completed rid=%s source_record_id=%s "
        "target_record_id=%s runbook_id=%s status=%s duration_ms=%d",
        http_rid(request),
        body.source_record_id,
        target_record_id,
        run.runbook_id,
        run.status,
        max(0, round((time.perf_counter() - started) * 1000)),
    )
    return run.model_dump(mode="json")


@router.post(
    "/investigation/records/{target_record_id}/runbook-shadow-runs",
    dependencies=[Depends(check_ingest_bearer)],
)
async def post_runbook_shadow_run(
    request: Request,
    target_record_id: int,
    body: RunbookShadowBody,
    settings: Settings = Depends(get_settings),
) -> Dict[str, Any]:
    """Replay an unapproved runbook read-only on one historical target."""
    started = time.perf_counter()
    logger.info(
        "runbook_event=api.shadow_requested rid=%s source_record_id=%s "
        "target_record_id=%s runbook_id=%s",
        http_rid(request),
        body.source_record_id,
        target_record_id,
        body.runbook_id,
    )
    try:
        shadow = await run_shadow_replay(settings, target_record_id, body)
    except Exception as exc:
        logger.warning(
            "runbook_event=api.shadow_failed rid=%s source_record_id=%s "
            "target_record_id=%s runbook_id=%s error_type=%s err=%s",
            http_rid(request),
            body.source_record_id,
            target_record_id,
            body.runbook_id,
            type(exc).__name__,
            exc,
            exc_info=_runbook_error_needs_trace(exc),
        )
        _raise_runbook_http(exc)
    logger.info(
        "runbook_event=api.shadow_completed rid=%s shadow_run_id=%s "
        "source_record_id=%s target_record_id=%s runbook_id=%s status=%s duration_ms=%d",
        http_rid(request),
        shadow.shadow_run_id,
        body.source_record_id,
        target_record_id,
        shadow.runbook_id,
        shadow.status,
        max(0, round((time.perf_counter() - started) * 1000)),
    )
    return shadow.model_dump(mode="json")
