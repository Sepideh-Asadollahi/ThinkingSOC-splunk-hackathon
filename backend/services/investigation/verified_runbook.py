"""Compile, verify, approve, and reuse evidence-grounded investigation runbooks."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Type, TypeVar
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from config import Settings, mcp_configured
from models.analysis import InvestigationQuestionItem
from models.runbook import (
    PortableRunbook,
    RunbookApproval,
    RunbookApprovalBody,
    RunbookCompatibleTarget,
    RunbookCompatibleTargets,
    RunbookEvaluationResponse,
    RunbookExportBundle,
    RunbookImportBody,
    RunbookImportResponse,
    RunbookLibraryGroup,
    RunbookLibraryItem,
    RunbookLibraryResponse,
    RunbookRevisionBody,
    RunbookRun,
    RunbookRunBody,
    RunbookRuntimeStatus,
    RunbookShadowBody,
    RunbookShadowRun,
    RunbookShadowRunSummary,
    RunbookStep,
    SafeResponseAction,
    SafeResponseDecision,
    SafeResponseDecisionBody,
    SafeResponsePreview,
    SafeResponsePreviewBody,
    VerifiedRunbookDraft,
    VerifiedRunbookState,
)
from services.investigation.investigation_workflow import (
    list_analyst_actions_for_record,
)
from services.llm.litellm_service import litellm_chat_completion
from services.soc_analysis.soc_analysis_json import parse_llm_json_response
from services.soc_analysis.soc_verdict import verdict_implies_false_positive
from services.splunk_json_store import (
    get_stored_event_by_id,
    search_stored_events,
    splunk_store_configured,
    submit_hec_event,
)

RUNBOOK_DRAFT_RECORD_TYPE = "verified_runbook_draft"
RUNBOOK_APPROVAL_RECORD_TYPE = "verified_runbook_approval"
RUNBOOK_RUN_RECORD_TYPE = "verified_runbook_run"
RUNBOOK_SHADOW_RUN_RECORD_TYPE = "verified_runbook_shadow_run"
RUNBOOK_RESPONSE_PREVIEW_RECORD_TYPE = "verified_runbook_response_preview"
RUNBOOK_RESPONSE_DECISION_RECORD_TYPE = "verified_runbook_response_decision"

logger = logging.getLogger(__name__)

_PROMPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "prompts"
    / "prompt_verified_runbook_system.md"
)
_RESPONSE_PROMPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "prompts"
    / "prompt_safe_response_preview_system.md"
)
_PROVIDER_KEY_ENV_NAMES = (
    "OPENAI_API_KEY",
    "AZURE_API_KEY",
    "ANTHROPIC_API_KEY",
    "GEMINI_API_KEY",
    "MISTRAL_API_KEY",
)
_SENSITIVE_FIELD_PARTS = (
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "credential",
)
_NON_DISRUPTIVE_RESPONSE_TYPES = {
    "COLLECT_FORENSICS",
    "ESCALATE_INCIDENT",
    "MONITOR_ONLY",
}
_ALL_RESPONSE_TYPES = {
    "ISOLATE_ENDPOINT",
    "DISABLE_ACCOUNT",
    "REVOKE_SESSIONS",
    "BLOCK_INDICATOR",
    "QUARANTINE_FILE",
    *_NON_DISRUPTIVE_RESPONSE_TYPES,
}
_FORBIDDEN_RESPONSE_TEXT = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"```",
        r"(?:^|\s)(?:curl|wget|powershell|pwsh|cmd\.exe|bash|sh)\s+",
        r"\b(?:rm\s+-rf|invoke-command|invoke-webrequest|netsh|reg\s+add)\b",
        r"\bsc(?:\.exe)?\s+(?:create|delete|stop|start)\b",
        r"\|\s*(?:search|delete|collect|outputlookup)\b",
    )
)


def _safe_log_value(value: Any, *, limit: int = 180) -> str:
    """Keep structured log fields single-line and bounded."""
    text = str(value).replace("\r", " ").replace("\n", " ").strip()
    return text if len(text) <= limit else f"{text[: limit - 3]}..."


def _log_runbook_event(
    event: str,
    *,
    level: int = logging.INFO,
    **fields: Any,
) -> None:
    """Emit grep-friendly lifecycle telemetry without alert bodies, SPL, or secrets."""
    parts = [f"runbook_event={_safe_log_value(event)}"]
    parts.extend(
        f"{key}={_safe_log_value(value)}"
        for key, value in fields.items()
        if value is not None
    )
    logger.log(level, " ".join(parts))


class VerifiedRunbookError(RuntimeError):
    """Expected domain failure with an HTTP-compatible status."""

    def __init__(self, message: str, *, status_code: int = 409) -> None:
        super().__init__(message)
        self.status_code = status_code


class _CompiledRunbookPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    summary: str = Field(min_length=1, max_length=2000)
    steps: List[RunbookStep] = Field(min_length=1, max_length=3)
    decision_rule: str = Field(min_length=1, max_length=2000)
    limitations: List[str] = Field(default_factory=list, max_length=10)


class _SafeResponsePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    actions: List[SafeResponseAction] = Field(min_length=1, max_length=5)
    decision_summary: str = Field(min_length=1, max_length=2000)
    limitations: List[str] = Field(default_factory=list, max_length=10)


T = TypeVar("T", bound=BaseModel)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _payload(row: Dict[str, Any]) -> Dict[str, Any]:
    value = row.get("payload")
    return value if isinstance(value, dict) else {}


def _analysis_context(row: Dict[str, Any]) -> tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    payload = _payload(row)
    analysis = payload.get("analysis") if isinstance(payload.get("analysis"), dict) else {}
    triage = payload.get("triage") if isinstance(payload.get("triage"), dict) else {}
    if not triage and isinstance(analysis.get("triage"), dict):
        triage = analysis["triage"]
    analysis_input = (
        payload.get("analysis_input")
        if isinstance(payload.get("analysis_input"), dict)
        else {}
    )
    return analysis, triage, analysis_input


def _source_verdict(analysis: Dict[str, Any], triage: Dict[str, Any]) -> str:
    judge = analysis.get("judge") if isinstance(analysis.get("judge"), dict) else {}
    return str(
        triage.get("review_verdict")
        or judge.get("verdict")
        or "needs_investigation"
    ).strip()


def _scrub_sensitive(value: Any) -> Any:
    """Remove credential-shaped keys before any source context reaches the LLM."""
    if isinstance(value, dict):
        return {
            str(key): _scrub_sensitive(item)
            for key, item in value.items()
            if not any(
                part in str(key).strip().lower()
                for part in _SENSITIVE_FIELD_PARTS
            )
        }
    if isinstance(value, list):
        return [_scrub_sensitive(item) for item in value]
    return value


def _safe_alert_fields(value: Any) -> Dict[str, Any]:
    scrubbed = _scrub_sensitive(value)
    return scrubbed if isinstance(scrubbed, dict) else {}


def _llm_runtime_configured(settings: Settings) -> bool:
    if not str(settings.litellm_model or "").strip():
        return False
    if settings.litellm_api_key or settings.litellm_api_base:
        return True
    return any(os.getenv(name) for name in _PROVIDER_KEY_ENV_NAMES)


def _ensure_feature_enabled(settings: Settings) -> None:
    if not settings.tsoc_runbook_enabled:
        raise VerifiedRunbookError(
            "ThinkingSOC Lite is disabled in Runbook settings.",
            status_code=503,
        )


def _ensure_verification_runtime(settings: Settings) -> None:
    if not splunk_store_configured(settings):
        raise VerifiedRunbookError(
            "PostgreSQL store not configured; set TSOC_POSTGRES_DSN.",
            status_code=503,
        )
    if not getattr(settings, "tsoc_execute_investigation_spl", True):
        raise VerifiedRunbookError(
            "Investigation SPL execution is disabled.",
            status_code=503,
        )
    if not settings.splunk_username or not settings.splunk_password:
        raise VerifiedRunbookError(
            "Splunk execution credentials are not configured.",
            status_code=503,
        )


def _ensure_runtime(settings: Settings) -> None:
    _ensure_verification_runtime(settings)
    if not _llm_runtime_configured(settings):
        raise VerifiedRunbookError(
            "LLM is not configured; set LITELLM_MODEL and provider credentials.",
            status_code=503,
        )


def _ensure_response_preview_runtime(settings: Settings) -> None:
    """Preview generation needs durable storage and an LLM, never Splunk execution."""
    if not splunk_store_configured(settings):
        raise VerifiedRunbookError(
            "PostgreSQL store not configured; set TSOC_POSTGRES_DSN.",
            status_code=503,
        )
    if not _llm_runtime_configured(settings):
        raise VerifiedRunbookError(
            "LLM is not configured; set LITELLM_MODEL and provider credentials.",
            status_code=503,
        )


def get_runbook_runtime_status(settings: Settings) -> RunbookRuntimeStatus:
    postgres_ready = splunk_store_configured(settings)
    llm_ready = _llm_runtime_configured(settings)
    splunk_ready = bool(settings.splunk_username and settings.splunk_password)
    execution_ready = bool(settings.tsoc_execute_investigation_spl)
    return RunbookRuntimeStatus(
        enabled=settings.tsoc_runbook_enabled,
        autopilot_enabled=settings.tsoc_runbook_autopilot_enabled,
        ready=bool(
            settings.tsoc_runbook_enabled
            and postgres_ready
            and llm_ready
            and splunk_ready
            and execution_ready
        ),
        configured_model=str(settings.litellm_model or ""),
        max_steps=settings.tsoc_runbook_max_steps,
        default_manual_minutes=settings.tsoc_runbook_default_manual_minutes,
        artifact_scan_limit=settings.tsoc_runbook_artifact_scan_limit,
        postgres_configured=postgres_ready,
        llm_configured=llm_ready,
        splunk_configured=splunk_ready,
        mcp_configured=mcp_configured(settings),
        rest_api_configured=splunk_ready,
        execution_enabled=execution_ready,
    )


async def _get_source_record(settings: Settings, record_id: int) -> Dict[str, Any]:
    row = await get_stored_event_by_id(settings, record_id)
    if row is None:
        raise VerifiedRunbookError("Record not found", status_code=404)
    if str(row.get("tsoc_record_type") or "") != "soc_analysis":
        raise VerifiedRunbookError(
            "Only stored soc_analysis records can produce a verified runbook."
        )

    analysis, triage, _ = _analysis_context(row)
    questions = analysis.get("investigation_questions")
    usable_questions = [
        item
        for item in questions or []
        if (
            isinstance(item, dict)
            and str(item.get("question") or "").strip()
        )
        or (not isinstance(item, dict) and str(item or "").strip())
    ]
    if not isinstance(questions, list) or not usable_questions:
        raise VerifiedRunbookError(
            "The investigation has no reusable investigation questions."
        )
    verdict = _source_verdict(analysis, triage)
    if str(triage.get("review_verdict") or "").upper() == "FALSE_POSITIVE":
        raise VerifiedRunbookError("False-positive investigations cannot become runbooks.")
    if verdict_implies_false_positive(verdict):
        raise VerifiedRunbookError("Benign investigations cannot become runbooks.")
    if not str(row.get("search_name") or "").strip():
        raise VerifiedRunbookError("The source investigation has no search_name.")

    actions = await list_analyst_actions_for_record(settings, record_id)
    latest = actions[0] if actions else None
    if not latest or latest.get("action") != "acknowledge":
        raise VerifiedRunbookError(
            "Acknowledge this investigation before building a runbook."
        )
    return row


def _minimized_source_snapshot(row: Dict[str, Any]) -> Dict[str, Any]:
    analysis, triage, analysis_input = _analysis_context(row)
    judge = analysis.get("judge") if isinstance(analysis.get("judge"), dict) else {}
    questions: List[Dict[str, Any]] = []
    for item in (analysis.get("investigation_questions") or [])[:3]:
        if isinstance(item, dict):
            questions.append(
                {
                    "question": item.get("question"),
                    "explanation": item.get("explanation"),
                    "pivots": item.get("pivots") or [],
                    "notes": item.get("notes") or [],
                }
            )
        elif str(item).strip():
            questions.append({"question": str(item).strip()})

    return _scrub_sensitive(
        {
            "source": {
                "record_id": row.get("id"),
                "search_name": row.get("search_name"),
                "summary": analysis.get("summary"),
                "verdict": judge,
                "triage": triage,
                "investigation_questions": questions,
                "evidence_chain": analysis.get("evidence_chain"),
                "alert_fields": _safe_alert_fields(analysis_input.get("alert_fields")),
            }
        }
    )


def _completion_json_text(output: Dict[str, Any]) -> str:
    for key in ("content", "thinking", "raw_content"):
        value = str(output.get(key) or "").strip()
        if value:
            return value
    return ""


async def _finalize_steps(*args: Any, **kwargs: Any) -> List[InvestigationQuestionItem]:
    """Load the existing SPL pipeline lazily to avoid graph package import cycles."""
    from services.investigation.investigation_questions_spl import (
        finalize_investigation_questions_for_verdict,
    )

    return await finalize_investigation_questions_for_verdict(*args, **kwargs)


def _parse_compiled_payload(
    output: Dict[str, Any], *, max_steps: int = 3
) -> _CompiledRunbookPayload:
    try:
        raw = parse_llm_json_response(_completion_json_text(output))
        compiled = _CompiledRunbookPayload.model_validate(raw)
        if len(compiled.steps) > max_steps:
            raise ValueError(
                f"runbook contains {len(compiled.steps)} steps; configured maximum is {max_steps}"
            )
        return compiled
    except (ValueError, ValidationError) as exc:
        raise VerifiedRunbookError(
            f"The LLM returned an invalid runbook: {exc}",
            status_code=502,
        ) from exc


def _response_text_values(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _response_text_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from _response_text_values(item)


def _parse_safe_response_payload(
    output: Dict[str, Any],
    *,
    allowed_action_types: Iterable[str],
) -> _SafeResponsePayload:
    """Validate a preview and reject command-like text or policy escalation."""
    try:
        raw = parse_llm_json_response(_completion_json_text(output))
        preview = _SafeResponsePayload.model_validate(raw)
    except (ValueError, ValidationError) as exc:
        raise VerifiedRunbookError(
            f"The LLM returned an invalid response preview: {exc}",
            status_code=502,
        ) from exc

    allowed = set(allowed_action_types)
    disallowed = sorted(
        {action.action_type for action in preview.actions if action.action_type not in allowed}
    )
    if disallowed:
        raise VerifiedRunbookError(
            "Response preview exceeded the evidence policy; disallowed action type(s): "
            + ", ".join(disallowed),
            status_code=502,
        )
    for text in _response_text_values(preview.model_dump(mode="json")):
        if any(pattern.search(text) for pattern in _FORBIDDEN_RESPONSE_TEXT):
            raise VerifiedRunbookError(
                "Response preview contained executable command or query syntax and was blocked.",
                status_code=502,
            )
    return preview


def derive_source_status(
    results: Iterable[InvestigationQuestionItem],
    *,
    expected_count: Optional[int] = None,
) -> str:
    items = list(results)
    if expected_count is not None and len(items) != expected_count:
        return "FAILED"
    if not items:
        return "DRAFT"
    if any(item.spl_results is not None and item.spl_results.error for item in items):
        return "FAILED"
    parser_valid = all(
        item.validation is not None and item.validation.valid is True for item in items
    )
    if not parser_valid:
        return "DRAFT"
    evidence_present = all(
        item.spl_results is not None
        and not item.spl_results.error
        and item.spl_results.row_count > 0
        for item in items
    )
    return "SOURCE_VERIFIED" if evidence_present else "PARSER_VALID"


def derive_run_status(
    results: Iterable[InvestigationQuestionItem],
    *,
    expected_count: Optional[int] = None,
) -> str:
    items = list(results)
    if expected_count is not None and len(items) != expected_count:
        return "FAILED"
    if not items or any(
        item.validation is None
        or item.validation.valid is not True
        or item.spl_results is None
        or bool(item.spl_results.error)
        for item in items
    ):
        return "FAILED"
    if all(
        item.validation is not None
        and item.validation.valid is True
        and item.spl_results is not None
        and not item.spl_results.error
        and item.spl_results.row_count > 0
        for item in items
    ):
        return "REUSED"
    return "NO_EVIDENCE"


def _result_metrics(
    results: Iterable[InvestigationQuestionItem],
) -> tuple[int, int, int]:
    items = list(results)
    parser_valid = sum(
        1
        for item in items
        if item.validation is not None and item.validation.valid is True
    )
    successful = sum(
        1
        for item in items
        if item.spl_results is not None
        and not item.spl_results.error
        and item.spl_results.row_count > 0
    )
    total_rows = sum(
        max(0, item.spl_results.row_count)
        for item in items
        if item.spl_results is not None and not item.spl_results.error
    )
    return parser_valid, successful, total_rows


def _execution_error_count(results: Iterable[InvestigationQuestionItem]) -> int:
    return sum(
        1
        for item in results
        if item.spl_results is not None and bool(item.spl_results.error)
    )


def _first_execution_error(
    results: Iterable[InvestigationQuestionItem],
) -> Optional[str]:
    for item in results:
        if item.spl_results is None or not item.spl_results.error:
            continue
        return _safe_log_value(str(item.spl_results.error), limit=500)
    return None


def _projected_savings(
    settings: Settings,
    *,
    duration_ms: int,
    estimated_manual_minutes: int,
) -> tuple[float, float]:
    automated_minutes = max(0.0, duration_ms / 60_000.0)
    minutes_saved = round(
        max(0.0, estimated_manual_minutes - automated_minutes),
        3,
    )
    labor_savings = round(
        minutes_saved / 60.0 * settings.tsoc_runbook_analyst_hourly_cost_usd,
        4,
    )
    return minutes_saved, labor_savings


async def _persist_model(
    settings: Settings,
    *,
    record_type: str,
    anchor: Dict[str, Any],
    model: BaseModel,
) -> None:
    runbook_id = getattr(model, "runbook_id", None)
    source_record_id = getattr(model, "source_record_id", None)
    target_record_id = getattr(model, "target_record_id", None)
    event = {
        "tsoc_record_type": record_type,
        "sid": anchor.get("sid"),
        "search_name": anchor.get("search_name"),
        "row_index": anchor.get("row_index"),
        **model.model_dump(mode="json"),
    }
    _log_runbook_event(
        "artifact.persist_started",
        record_type=record_type,
        runbook_id=runbook_id,
        source_record_id=source_record_id,
        target_record_id=target_record_id,
    )
    try:
        persisted = await submit_hec_event(settings, event)
    except Exception as exc:
        _log_runbook_event(
            "artifact.persist_failed",
            level=logging.ERROR,
            record_type=record_type,
            runbook_id=runbook_id,
            error_type=type(exc).__name__,
        )
        raise
    if not persisted:
        _log_runbook_event(
            "artifact.persist_failed",
            level=logging.WARNING,
            record_type=record_type,
            runbook_id=runbook_id,
            reason="store_returned_false",
        )
        raise VerifiedRunbookError(
            f"Failed to persist {record_type}.",
            status_code=502,
        )
    _log_runbook_event(
        "artifact.persisted",
        record_type=record_type,
        runbook_id=runbook_id,
        source_record_id=source_record_id,
        target_record_id=target_record_id,
    )
    from services.soc_rag.index_writer import schedule_runbook_artifact_index

    schedule_runbook_artifact_index(
        settings,
        record_type=record_type,
        event=event,
    )
    _log_runbook_event(
        "artifact.chat_index_scheduled",
        record_type=record_type,
        runbook_id=runbook_id,
    )


def _model_from_row(model_type: Type[T], row: Dict[str, Any]) -> Optional[T]:
    try:
        return model_type.model_validate(_payload(row))
    except ValidationError as exc:
        _log_runbook_event(
            "artifact.validation_skipped",
            level=logging.WARNING,
            model=model_type.__name__,
            storage_record_id=row.get("id"),
            validation_error_count=exc.error_count(),
        )
        return None


async def _artifact_rows(settings: Settings, record_type: str) -> List[Dict[str, Any]]:
    started = time.perf_counter()
    rows = await search_stored_events(
        settings,
        record_type=record_type,
        limit=settings.tsoc_runbook_artifact_scan_limit,
        order="desc",
    )
    _log_runbook_event(
        "artifact.scan_completed",
        level=logging.DEBUG,
        record_type=record_type,
        row_count=len(rows),
        duration_ms=max(0, round((time.perf_counter() - started) * 1000)),
    )
    return rows


async def _latest_draft(
    settings: Settings, source_record_id: int
) -> Optional[VerifiedRunbookDraft]:
    for row in await _artifact_rows(settings, RUNBOOK_DRAFT_RECORD_TYPE):
        payload = _payload(row)
        if payload.get("source_record_id") not in (source_record_id, str(source_record_id)):
            continue
        model = _model_from_row(VerifiedRunbookDraft, row)
        if model is not None:
            return model
    return None


async def _draft_by_id(
    settings: Settings, runbook_id: str
) -> Optional[VerifiedRunbookDraft]:
    for row in await _artifact_rows(settings, RUNBOOK_DRAFT_RECORD_TYPE):
        if _payload(row).get("runbook_id") != runbook_id:
            continue
        model = _model_from_row(VerifiedRunbookDraft, row)
        if model is not None:
            return model
    return None


async def _latest_approval(
    settings: Settings,
    source_record_id: int,
    runbook_id: Optional[str] = None,
) -> Optional[RunbookApproval]:
    for row in await _artifact_rows(settings, RUNBOOK_APPROVAL_RECORD_TYPE):
        payload = _payload(row)
        if payload.get("source_record_id") not in (source_record_id, str(source_record_id)):
            continue
        if runbook_id and payload.get("runbook_id") != runbook_id:
            continue
        model = _model_from_row(RunbookApproval, row)
        if model is not None:
            return model
    return None


async def _latest_run(
    settings: Settings,
    source_record_id: int,
    runbook_id: Optional[str] = None,
) -> Optional[RunbookRun]:
    for row in await _artifact_rows(settings, RUNBOOK_RUN_RECORD_TYPE):
        payload = _payload(row)
        if payload.get("source_record_id") not in (source_record_id, str(source_record_id)):
            continue
        if runbook_id and payload.get("runbook_id") != runbook_id:
            continue
        model = _model_from_row(RunbookRun, row)
        if model is not None:
            return model
    return None


async def _latest_response_preview(
    settings: Settings,
    source_record_id: int,
    runbook_id: Optional[str] = None,
) -> Optional[SafeResponsePreview]:
    for row in await _artifact_rows(settings, RUNBOOK_RESPONSE_PREVIEW_RECORD_TYPE):
        payload = _payload(row)
        if payload.get("source_record_id") not in (source_record_id, str(source_record_id)):
            continue
        if runbook_id and payload.get("runbook_id") != runbook_id:
            continue
        model = _model_from_row(SafeResponsePreview, row)
        if model is not None:
            return model
    return None


async def _latest_response_decision(
    settings: Settings,
    source_record_id: int,
    preview_id: Optional[str] = None,
) -> Optional[SafeResponseDecision]:
    for row in await _artifact_rows(settings, RUNBOOK_RESPONSE_DECISION_RECORD_TYPE):
        payload = _payload(row)
        if payload.get("source_record_id") not in (source_record_id, str(source_record_id)):
            continue
        if preview_id and payload.get("preview_id") != preview_id:
            continue
        model = _model_from_row(SafeResponseDecision, row)
        if model is not None:
            return model
    return None


async def build_verified_runbook(
    settings: Settings, record_id: int
) -> VerifiedRunbookDraft:
    _log_runbook_event(
        "compile.requested",
        source_record_id=record_id,
        enabled=settings.tsoc_runbook_enabled,
        configured_model=settings.litellm_model,
        max_steps=settings.tsoc_runbook_max_steps,
    )
    _ensure_feature_enabled(settings)
    _ensure_runtime(settings)
    source = await _get_source_record(settings, record_id)
    analysis, triage, analysis_input = _analysis_context(source)
    verdict = _source_verdict(analysis, triage)
    started = time.perf_counter()
    _log_runbook_event(
        "compile.source_ready",
        source_record_id=record_id,
        search_name=source.get("search_name"),
        verdict=verdict,
        question_count=len(analysis.get("investigation_questions") or []),
    )

    prompt = _PROMPT_PATH.read_text(encoding="utf-8")
    generation_started = time.perf_counter()
    source_snapshot = _minimized_source_snapshot(source)
    source_snapshot["compiler_policy"] = {
        "max_steps": settings.tsoc_runbook_max_steps,
        "intent_only": True,
        "read_only": True,
    }
    max_tokens = min(8192, settings.litellm_analysis_max_tokens)
    _log_runbook_event(
        "compile.generation_started",
        source_record_id=record_id,
        model=settings.litellm_model,
        max_tokens=max_tokens,
    )
    try:
        output = await litellm_chat_completion(
            settings,
            [
                {"role": "system", "content": prompt},
                {
                    "role": "user",
                    "content": json.dumps(
                        source_snapshot,
                        ensure_ascii=False,
                        separators=(",", ":"),
                        default=str,
                    ),
                },
            ],
            temperature=settings.litellm_analysis_temperature,
            max_tokens=max_tokens,
        )
    except Exception as exc:
        _log_runbook_event(
            "compile.generation_failed",
            level=logging.WARNING,
            source_record_id=record_id,
            duration_ms=max(0, round((time.perf_counter() - generation_started) * 1000)),
            error_type=type(exc).__name__,
        )
        raise
    generation_duration_ms = max(
        0, round((time.perf_counter() - generation_started) * 1000)
    )
    compiled = _parse_compiled_payload(
        output,
        max_steps=settings.tsoc_runbook_max_steps,
    )
    usage = output.get("usage") if isinstance(output.get("usage"), dict) else {}
    _log_runbook_event(
        "compile.generation_completed",
        source_record_id=record_id,
        model=output.get("model") or settings.litellm_model,
        step_count=len(compiled.steps),
        prompt_tokens=usage.get("prompt_tokens"),
        completion_tokens=usage.get("completion_tokens"),
        duration_ms=generation_duration_ms,
    )
    intents = [step.intent for step in compiled.steps]
    verification_started = time.perf_counter()
    _log_runbook_event(
        "compile.verification_started",
        source_record_id=record_id,
        step_count=len(compiled.steps),
        search_name=source.get("search_name"),
    )
    try:
        source_results = await _finalize_steps(
            settings,
            verdict,
            intents,
            max_items=settings.tsoc_runbook_max_steps,
            normalized=_safe_alert_fields(analysis_input.get("alert_fields")),
            search_name=str(source.get("search_name") or ""),
            sid=source.get("sid"),
            splunk_results=[],
            defender_output={"defender": analysis.get("defender")},
            hunter_output=(
                analysis.get("hunter")
                if isinstance(analysis.get("hunter"), dict)
                else {}
            ),
            judge_output=(
                analysis.get("judge")
                if isinstance(analysis.get("judge"), dict)
                else {}
            ),
        )
    except Exception as exc:
        _log_runbook_event(
            "compile.verification_failed",
            level=logging.WARNING,
            source_record_id=record_id,
            duration_ms=max(
                0, round((time.perf_counter() - verification_started) * 1000)
            ),
            error_type=type(exc).__name__,
        )
        raise
    verification_duration_ms = max(
        0, round((time.perf_counter() - verification_started) * 1000)
    )
    parser_valid, successful, total_rows = _result_metrics(source_results)
    source_status = derive_source_status(
        source_results,
        expected_count=len(compiled.steps),
    )
    _log_runbook_event(
        "compile.verification_completed",
        source_record_id=record_id,
        status=source_status,
        step_count=len(compiled.steps),
        parser_valid_step_count=parser_valid,
        successful_step_count=successful,
        total_evidence_rows=total_rows,
        duration_ms=verification_duration_ms,
    )
    previous = await _latest_draft(settings, record_id)
    draft = VerifiedRunbookDraft(
        runbook_id=str(uuid4()),
        source_record_id=record_id,
        title=compiled.title,
        summary=compiled.summary,
        applicable_search_name=str(source.get("search_name") or ""),
        source_verdict=verdict,
        steps=compiled.steps,
        decision_rule=compiled.decision_rule,
        limitations=compiled.limitations,
        source_results=source_results,
        status=source_status,
        configured_model=str(settings.litellm_model or ""),
        model=str(output.get("model") or settings.litellm_model),
        prompt_tokens=usage.get("prompt_tokens"),
        completion_tokens=usage.get("completion_tokens"),
        generation_duration_ms=generation_duration_ms,
        verification_duration_ms=verification_duration_ms,
        compile_duration_ms=max(0, round((time.perf_counter() - started) * 1000)),
        parser_valid_step_count=parser_valid,
        successful_step_count=successful,
        total_evidence_rows=total_rows,
        revision=(previous.revision + 1 if previous else 1),
        parent_runbook_id=(previous.runbook_id if previous else None),
        origin="compiled",
        created_at=_utc_now(),
    )
    await _persist_model(
        settings,
        record_type=RUNBOOK_DRAFT_RECORD_TYPE,
        anchor=source,
        model=draft,
    )
    _log_runbook_event(
        "compile.completed",
        source_record_id=record_id,
        runbook_id=draft.runbook_id,
        revision=draft.revision,
        status=draft.status,
        step_count=len(draft.steps),
        compile_duration_ms=draft.compile_duration_ms,
    )
    return draft


def _portable_runbook(draft: VerifiedRunbookDraft) -> PortableRunbook:
    """Project a stored artifact to the intentionally evidence-free exchange schema."""
    return PortableRunbook(
        original_runbook_id=draft.runbook_id,
        original_source_record_id=(
            draft.source_record_id if draft.source_record_id > 0 else None
        ),
        title=draft.title,
        summary=draft.summary,
        applicable_search_name=draft.applicable_search_name,
        steps=draft.steps,
        decision_rule=draft.decision_rule,
        limitations=draft.limitations,
        source_verdict=draft.source_verdict,
        revision=draft.revision,
        created_at=draft.created_at,
    )


async def list_runbook_library(
    settings: Settings,
    *,
    search_name: Optional[str] = None,
) -> RunbookLibraryResponse:
    """List every valid artifact grouped by its exact alert/search name."""
    started = time.perf_counter()
    _log_runbook_event(
        "library.requested",
        search_name=search_name,
        scan_limit=settings.tsoc_runbook_artifact_scan_limit,
    )
    if not splunk_store_configured(settings):
        raise VerifiedRunbookError(
            "PostgreSQL store not configured; set TSOC_POSTGRES_DSN.",
            status_code=503,
        )
    draft_rows, approval_rows, run_rows = await asyncio.gather(
        _artifact_rows(settings, RUNBOOK_DRAFT_RECORD_TYPE),
        _artifact_rows(settings, RUNBOOK_APPROVAL_RECORD_TYPE),
        _artifact_rows(settings, RUNBOOK_RUN_RECORD_TYPE),
    )
    drafts = [
        model
        for row in draft_rows
        if (model := _model_from_row(VerifiedRunbookDraft, row)) is not None
    ]
    requested = str(search_name or "").strip()
    if requested:
        drafts = [item for item in drafts if item.applicable_search_name == requested]

    latest_approval: Dict[str, RunbookApproval] = {}
    for row in approval_rows:
        model = _model_from_row(RunbookApproval, row)
        if model is not None and model.runbook_id not in latest_approval:
            latest_approval[model.runbook_id] = model
    latest_run: Dict[str, RunbookRun] = {}
    for row in run_rows:
        model = _model_from_row(RunbookRun, row)
        if model is not None and model.runbook_id not in latest_run:
            latest_run[model.runbook_id] = model

    latest_for_source: set[str] = set()
    seen_sources: set[int] = set()
    parent_ids = {
        draft.parent_runbook_id
        for draft in drafts
        if draft.parent_runbook_id is not None
    }
    for draft in drafts:
        if draft.source_record_id <= 0 and draft.runbook_id not in parent_ids:
            latest_for_source.add(draft.runbook_id)
        elif draft.source_record_id not in seen_sources:
            seen_sources.add(draft.source_record_id)
            latest_for_source.add(draft.runbook_id)

    grouped: Dict[str, List[RunbookLibraryItem]] = {}
    for draft in drafts:
        grouped.setdefault(draft.applicable_search_name, []).append(
            RunbookLibraryItem(
                draft=draft,
                latest_approval=latest_approval.get(draft.runbook_id),
                latest_run=latest_run.get(draft.runbook_id),
                is_latest_for_source=draft.runbook_id in latest_for_source,
            )
        )
    groups = [
        RunbookLibraryGroup(alert_name=name, count=len(items), runbooks=items)
        for name, items in sorted(grouped.items(), key=lambda entry: entry[0].lower())
    ]
    response = RunbookLibraryResponse(
        count=sum(group.count for group in groups),
        alert_count=len(groups),
        groups=groups,
    )
    _log_runbook_event(
        "library.completed",
        search_name=search_name,
        runbook_count=response.count,
        alert_count=response.alert_count,
        duration_ms=max(0, round((time.perf_counter() - started) * 1000)),
    )
    return response


async def get_runbook_evaluation(settings: Settings) -> RunbookEvaluationResponse:
    """Aggregate persisted compiler, replay, approval, and reuse evidence."""
    started = time.perf_counter()
    _log_runbook_event(
        "evaluation.requested",
        scan_limit=settings.tsoc_runbook_artifact_scan_limit,
    )
    if not splunk_store_configured(settings):
        raise VerifiedRunbookError(
            "PostgreSQL store not configured; set TSOC_POSTGRES_DSN.",
            status_code=503,
        )

    draft_rows, approval_rows, run_rows, shadow_rows = await asyncio.gather(
        _artifact_rows(settings, RUNBOOK_DRAFT_RECORD_TYPE),
        _artifact_rows(settings, RUNBOOK_APPROVAL_RECORD_TYPE),
        _artifact_rows(settings, RUNBOOK_RUN_RECORD_TYPE),
        _artifact_rows(settings, RUNBOOK_SHADOW_RUN_RECORD_TYPE),
    )
    drafts = [
        model
        for row in draft_rows
        if (model := _model_from_row(VerifiedRunbookDraft, row)) is not None
    ]
    approvals = [
        model
        for row in approval_rows
        if (model := _model_from_row(RunbookApproval, row)) is not None
    ]
    runs = [
        model
        for row in run_rows
        if (model := _model_from_row(RunbookRun, row)) is not None
    ]
    shadow_runs = [
        model
        for row in shadow_rows
        if (model := _model_from_row(RunbookShadowRun, row)) is not None
    ]

    parent_ids = {
        draft.parent_runbook_id
        for draft in drafts
        if draft.parent_runbook_id is not None
    }
    latest_runbook_count = 0
    seen_sources: set[int] = set()
    for draft in drafts:
        if draft.source_record_id > 0:
            if draft.source_record_id in seen_sources:
                continue
            seen_sources.add(draft.source_record_id)
            latest_runbook_count += 1
        elif draft.runbook_id not in parent_ids:
            latest_runbook_count += 1

    total_steps = sum(len(draft.steps) for draft in drafts)
    parser_valid_steps = sum(
        min(len(draft.steps), draft.parser_valid_step_count) for draft in drafts
    )
    shadow_evidence_count = sum(
        1 for shadow in shadow_runs if shadow.total_evidence_rows > 0
    )
    total_execution_errors = sum(
        shadow.execution_error_count for shadow in shadow_runs
    ) + sum(_execution_error_count(run.results) for run in runs)
    status_breakdown: Dict[str, int] = {
        "EVIDENCE_FOUND": 0,
        "NO_EVIDENCE": 0,
        "FAILED": 0,
    }
    for shadow in shadow_runs:
        status_breakdown[shadow.status] = status_breakdown.get(shadow.status, 0) + 1

    total_prompt_tokens = sum(max(0, draft.prompt_tokens or 0) for draft in drafts)
    total_completion_tokens = sum(
        max(0, draft.completion_tokens or 0) for draft in drafts
    )
    estimated_compile_llm_cost = round(
        total_prompt_tokens
        * settings.tsoc_runbook_input_cost_per_1m_tokens
        / 1_000_000
        + total_completion_tokens
        * settings.tsoc_runbook_output_cost_per_1m_tokens
        / 1_000_000,
        6,
    )
    response = RunbookEvaluationResponse(
        generated_at=_utc_now(),
        revision_count=len(drafts),
        alert_count=len({draft.applicable_search_name for draft in drafts}),
        latest_runbook_count=latest_runbook_count,
        approved_runbook_count=len(
            {approval.runbook_id for approval in approvals if approval.decision == "approve"}
        ),
        production_run_count=len(runs),
        shadow_run_count=len(shadow_runs),
        source_verified_revision_count=sum(
            1 for draft in drafts if draft.status == "SOURCE_VERIFIED"
        ),
        parser_valid_revision_count=sum(
            1
            for draft in drafts
            if draft.status in ("PARSER_VALID", "SOURCE_VERIFIED")
        ),
        failed_revision_count=sum(1 for draft in drafts if draft.status == "FAILED"),
        total_step_count=total_steps,
        parser_valid_step_count=parser_valid_steps,
        parser_valid_rate=(
            round(parser_valid_steps / total_steps * 100.0, 2) if total_steps else 0.0
        ),
        shadow_evidence_run_count=shadow_evidence_count,
        evidence_coverage_rate=(
            round(shadow_evidence_count / len(shadow_runs) * 100.0, 2)
            if shadow_runs
            else 0.0
        ),
        total_shadow_evidence_rows=sum(
            shadow.total_evidence_rows for shadow in shadow_runs
        ),
        total_execution_errors=total_execution_errors,
        average_compile_duration_ms=(
            round(
                sum(draft.compile_duration_ms for draft in drafts) / len(drafts),
                2,
            )
            if drafts
            else 0.0
        ),
        average_shadow_duration_ms=(
            round(sum(shadow.duration_ms for shadow in shadow_runs) / len(shadow_runs), 2)
            if shadow_runs
            else 0.0
        ),
        projected_minutes_saved=round(
            sum(shadow.projected_minutes_saved for shadow in shadow_runs),
            3,
        ),
        projected_labor_savings_usd=round(
            sum(shadow.projected_labor_savings_usd for shadow in shadow_runs),
            4,
        ),
        realized_minutes_saved=round(
            sum(run.estimated_minutes_saved for run in runs),
            3,
        ),
        total_prompt_tokens=total_prompt_tokens,
        total_completion_tokens=total_completion_tokens,
        estimated_compile_llm_cost_usd=estimated_compile_llm_cost,
        analyst_hourly_cost_usd=settings.tsoc_runbook_analyst_hourly_cost_usd,
        shadow_status_breakdown=status_breakdown,
        recent_shadow_runs=[
            RunbookShadowRunSummary.model_validate(shadow.model_dump())
            for shadow in shadow_runs[:10]
        ],
    )
    _log_runbook_event(
        "evaluation.completed",
        revision_count=response.revision_count,
        shadow_run_count=response.shadow_run_count,
        parser_valid_rate=response.parser_valid_rate,
        evidence_coverage_rate=response.evidence_coverage_rate,
        duration_ms=max(0, round((time.perf_counter() - started) * 1000)),
    )
    return response


async def export_runbooks(
    settings: Settings,
    *,
    runbook_id: Optional[str] = None,
    search_name: Optional[str] = None,
) -> RunbookExportBundle:
    """Export selected runbooks using the stable, intent-only v1 schema."""
    started = time.perf_counter()
    _log_runbook_event(
        "export.requested",
        runbook_id=runbook_id,
        search_name=search_name,
    )
    library = await list_runbook_library(settings, search_name=search_name)
    drafts = [item.draft for group in library.groups for item in group.runbooks]
    if runbook_id:
        drafts = [draft for draft in drafts if draft.runbook_id == runbook_id]
    if not drafts:
        raise VerifiedRunbookError("No runbooks matched the export filter.", status_code=404)
    if len(drafts) > 100:
        raise VerifiedRunbookError(
            "Export is limited to 100 runbooks; filter by Alert Name.",
            status_code=422,
        )
    document = RunbookExportBundle(
        exported_at=_utc_now(),
        runbooks=[_portable_runbook(draft) for draft in drafts],
    )
    _log_runbook_event(
        "export.completed",
        runbook_id=runbook_id,
        search_name=search_name,
        exported_count=len(document.runbooks),
        duration_ms=max(0, round((time.perf_counter() - started) * 1000)),
    )
    return document


async def _verify_manual_steps(
    settings: Settings,
    source: Dict[str, Any],
    steps: List[RunbookStep],
) -> tuple[List[InvestigationQuestionItem], str, int]:
    analysis, triage, analysis_input = _analysis_context(source)
    verdict = _source_verdict(analysis, triage)
    started = time.perf_counter()
    results = await _finalize_steps(
        settings,
        verdict,
        [step.intent for step in steps],
        normalized=_safe_alert_fields(analysis_input.get("alert_fields")),
        search_name=str(source.get("search_name") or ""),
        sid=source.get("sid"),
        splunk_results=[],
        defender_output={"defender": analysis.get("defender")},
        hunter_output=(
            analysis.get("hunter") if isinstance(analysis.get("hunter"), dict) else {}
        ),
        judge_output=(
            analysis.get("judge") if isinstance(analysis.get("judge"), dict) else {}
        ),
    )
    return results, verdict, max(0, round((time.perf_counter() - started) * 1000))


async def import_runbooks(
    settings: Settings,
    body: RunbookImportBody,
) -> RunbookImportResponse:
    """Import portable artifacts as inert drafts or source-verified local copies."""
    operation_started = time.perf_counter()
    _log_runbook_event(
        "import.requested",
        import_count=len(body.document.runbooks),
        source_record_id=body.source_record_id,
        verify_on_source=body.verify_on_source,
    )
    _ensure_feature_enabled(settings)
    if not splunk_store_configured(settings):
        raise VerifiedRunbookError(
            "PostgreSQL store not configured; set TSOC_POSTGRES_DSN.",
            status_code=503,
        )
    if body.source_record_id and len(body.document.runbooks) != 1:
        raise VerifiedRunbookError(
            "Attach and verify one imported runbook at a time.", status_code=422
        )
    if body.verify_on_source and not body.source_record_id:
        raise VerifiedRunbookError(
            "source_record_id is required when verify_on_source is enabled.",
            status_code=422,
        )
    if body.verify_on_source:
        _ensure_verification_runtime(settings)

    source = (
        await _get_source_record(settings, body.source_record_id)
        if body.source_record_id
        else None
    )
    imported: List[VerifiedRunbookDraft] = []
    for item_index, portable in enumerate(body.document.runbooks, start=1):
        if source and str(source.get("search_name") or "") != portable.applicable_search_name:
            raise VerifiedRunbookError(
                "Imported Alert Name must exactly match the attached source search_name."
            )
        started = time.perf_counter()
        results: List[InvestigationQuestionItem] = []
        verdict = portable.source_verdict
        verification_ms = 0
        if source and body.verify_on_source:
            _log_runbook_event(
                "import.verification_started",
                item_index=item_index,
                source_record_id=body.source_record_id,
                step_count=len(portable.steps),
                search_name=portable.applicable_search_name,
            )
            results, verdict, verification_ms = await _verify_manual_steps(
                settings, source, portable.steps
            )
        parser_valid, successful, total_rows = _result_metrics(results)
        status = (
            derive_source_status(results, expected_count=len(portable.steps))
            if body.verify_on_source
            else "DRAFT"
        )
        draft = VerifiedRunbookDraft(
            runbook_id=str(uuid4()),
            source_record_id=body.source_record_id or 0,
            title=portable.title,
            summary=portable.summary,
            applicable_search_name=portable.applicable_search_name,
            source_verdict=verdict,
            steps=portable.steps,
            decision_rule=portable.decision_rule,
            limitations=portable.limitations,
            source_results=results,
            status=status,
            configured_model=str(settings.litellm_model or "") or None,
            model="portable-import",
            verification_duration_ms=verification_ms,
            compile_duration_ms=max(0, round((time.perf_counter() - started) * 1000)),
            parser_valid_step_count=parser_valid,
            successful_step_count=successful,
            total_evidence_rows=total_rows,
            revision=1,
            origin="imported",
            revision_note=(body.note or "").strip() or None,
            edited_by=body.imported_by.strip(),
            imported_from_runbook_id=portable.original_runbook_id,
            created_at=_utc_now(),
        )
        await _persist_model(
            settings,
            record_type=RUNBOOK_DRAFT_RECORD_TYPE,
            anchor=source or {"search_name": portable.applicable_search_name},
            model=draft,
        )
        imported.append(draft)
        _log_runbook_event(
            "import.item_completed",
            item_index=item_index,
            runbook_id=draft.runbook_id,
            source_record_id=draft.source_record_id,
            status=draft.status,
            step_count=len(draft.steps),
            parser_valid_step_count=parser_valid,
            successful_step_count=successful,
            total_evidence_rows=total_rows,
            duration_ms=draft.compile_duration_ms,
        )
    response = RunbookImportResponse(imported_count=len(imported), runbooks=imported)
    _log_runbook_event(
        "import.completed",
        imported_count=response.imported_count,
        source_record_id=body.source_record_id,
        verify_on_source=body.verify_on_source,
        duration_ms=max(0, round((time.perf_counter() - operation_started) * 1000)),
    )
    return response


async def revise_runbook(
    settings: Settings,
    runbook_id: str,
    body: RunbookRevisionBody,
) -> VerifiedRunbookDraft:
    """Persist a complete edit as a new revision with a fresh approval boundary."""
    operation_started = time.perf_counter()
    _log_runbook_event(
        "revision.requested",
        parent_runbook_id=runbook_id,
        requested_source_record_id=body.source_record_id,
        verify_on_source=body.verify_on_source,
        step_count=len(body.steps),
    )
    _ensure_feature_enabled(settings)
    if not splunk_store_configured(settings):
        raise VerifiedRunbookError(
            "PostgreSQL store not configured; set TSOC_POSTGRES_DSN.",
            status_code=503,
        )
    parent = await _draft_by_id(settings, runbook_id)
    if parent is None:
        raise VerifiedRunbookError("Runbook not found.", status_code=404)
    if parent.source_record_id > 0 and body.source_record_id not in (
        None,
        parent.source_record_id,
    ):
        raise VerifiedRunbookError("An attached runbook cannot be rebound to another source.")
    source_record_id = parent.source_record_id or body.source_record_id or 0
    source = await _get_source_record(settings, source_record_id) if source_record_id else None
    if source and str(source.get("search_name") or "") != body.applicable_search_name:
        raise VerifiedRunbookError(
            "Edited Alert Name must exactly match the attached source search_name."
        )
    if body.verify_on_source and source is None:
        raise VerifiedRunbookError(
            "Attach a source record before source verification.", status_code=422
        )
    if body.verify_on_source:
        _ensure_verification_runtime(settings)

    started = time.perf_counter()
    results: List[InvestigationQuestionItem] = []
    verdict = parent.source_verdict
    verification_ms = 0
    if source and body.verify_on_source:
        _log_runbook_event(
            "revision.verification_started",
            parent_runbook_id=runbook_id,
            source_record_id=source_record_id,
            step_count=len(body.steps),
        )
        results, verdict, verification_ms = await _verify_manual_steps(
            settings, source, body.steps
        )
    parser_valid, successful, total_rows = _result_metrics(results)
    draft = VerifiedRunbookDraft(
        runbook_id=str(uuid4()),
        source_record_id=source_record_id,
        title=body.title,
        summary=body.summary,
        applicable_search_name=body.applicable_search_name,
        source_verdict=verdict,
        steps=body.steps,
        decision_rule=body.decision_rule,
        limitations=body.limitations,
        source_results=results,
        status=(
            derive_source_status(results, expected_count=len(body.steps))
            if body.verify_on_source
            else "DRAFT"
        ),
        configured_model=str(settings.litellm_model or "") or None,
        model="manual-editor",
        verification_duration_ms=verification_ms,
        compile_duration_ms=max(0, round((time.perf_counter() - started) * 1000)),
        parser_valid_step_count=parser_valid,
        successful_step_count=successful,
        total_evidence_rows=total_rows,
        revision=parent.revision + 1,
        parent_runbook_id=parent.runbook_id,
        origin="edited",
        revision_note=(body.revision_note or "").strip() or None,
        edited_by=body.editor.strip(),
        created_at=_utc_now(),
    )
    await _persist_model(
        settings,
        record_type=RUNBOOK_DRAFT_RECORD_TYPE,
        anchor=source or {"search_name": body.applicable_search_name},
        model=draft,
    )
    _log_runbook_event(
        "revision.completed",
        parent_runbook_id=runbook_id,
        runbook_id=draft.runbook_id,
        source_record_id=source_record_id,
        revision=draft.revision,
        status=draft.status,
        parser_valid_step_count=parser_valid,
        successful_step_count=successful,
        total_evidence_rows=total_rows,
        duration_ms=max(0, round((time.perf_counter() - operation_started) * 1000)),
    )
    return draft


async def get_verified_runbook_state(
    settings: Settings, record_id: int
) -> VerifiedRunbookState:
    started = time.perf_counter()
    if not splunk_store_configured(settings):
        raise VerifiedRunbookError(
            "PostgreSQL store not configured; set TSOC_POSTGRES_DSN.",
            status_code=503,
        )
    if await get_stored_event_by_id(settings, record_id) is None:
        raise VerifiedRunbookError("Record not found", status_code=404)
    draft = await _latest_draft(settings, record_id)
    runbook_id = draft.runbook_id if draft else None
    response_preview = (
        await _latest_response_preview(settings, record_id, runbook_id) if draft else None
    )
    state = VerifiedRunbookState(
        record_id=record_id,
        draft=draft,
        latest_approval=(
            await _latest_approval(settings, record_id, runbook_id) if draft else None
        ),
        latest_run=(
            await _latest_run(settings, record_id, runbook_id) if draft else None
        ),
        latest_response_preview=response_preview,
        latest_response_decision=(
            await _latest_response_decision(
                settings,
                record_id,
                response_preview.preview_id,
            )
            if response_preview
            else None
        ),
    )
    _log_runbook_event(
        "state.loaded",
        level=logging.DEBUG,
        source_record_id=record_id,
        runbook_id=runbook_id,
        has_draft=state.draft is not None,
        has_approval=state.latest_approval is not None,
        has_run=state.latest_run is not None,
        has_response_preview=state.latest_response_preview is not None,
        has_response_decision=state.latest_response_decision is not None,
        duration_ms=max(0, round((time.perf_counter() - started) * 1000)),
    )
    return state


async def list_compatible_runbook_targets(
    settings: Settings,
    source_record_id: int,
    *,
    limit: int = 12,
) -> RunbookCompatibleTargets:
    """Return bounded, exact-detection reuse candidates without exposing payloads."""
    started = time.perf_counter()
    _log_runbook_event(
        "compatible_targets.requested",
        source_record_id=source_record_id,
        requested_limit=limit,
    )
    if not splunk_store_configured(settings):
        raise VerifiedRunbookError(
            "PostgreSQL store not configured; set TSOC_POSTGRES_DSN.",
            status_code=503,
        )
    source = await get_stored_event_by_id(settings, source_record_id)
    if source is None:
        raise VerifiedRunbookError("Record not found", status_code=404)
    if str(source.get("tsoc_record_type") or "") != "soc_analysis":
        raise VerifiedRunbookError(
            "Only stored soc_analysis records can have compatible runbook targets."
        )
    search_name = str(source.get("search_name") or "").strip()
    if not search_name:
        raise VerifiedRunbookError("The source investigation has no search_name.")
    source_sid = str(source.get("sid") or "").strip()

    requested_limit = max(1, min(int(limit), 50))
    scan_limit = max(requested_limit, settings.tsoc_runbook_artifact_scan_limit)
    candidates: List[RunbookCompatibleTarget] = []
    for row in await search_stored_events(
        settings,
        record_type="soc_analysis",
        limit=scan_limit,
        order="desc",
    ):
        if row.get("id") in (source_record_id, str(source_record_id)):
            continue
        if str(row.get("search_name") or "").strip() != search_name:
            continue
        candidate_sid = str(row.get("sid") or "").strip()
        if source_sid and candidate_sid == source_sid:
            # A second stored row can represent the same Splunk alert. Reuse is
            # meaningful only across distinct alert instances, identified by SID.
            continue
        analysis, triage, _ = _analysis_context(row)
        summary = str(analysis.get("summary") or "").strip() or None
        verdict = _source_verdict(analysis, triage)
        candidates.append(
            RunbookCompatibleTarget(
                record_id=int(row["id"]),
                created_at=(str(row.get("created_at")) if row.get("created_at") else None),
                sid=(str(row.get("sid")) if row.get("sid") else None),
                search_name=search_name,
                row_index=(int(row["row_index"]) if row.get("row_index") is not None else None),
                summary=summary,
                review_verdict=verdict or None,
            )
        )
        if len(candidates) >= requested_limit:
            break

    response = RunbookCompatibleTargets(
        source_record_id=source_record_id,
        search_name=search_name,
        count=len(candidates),
        results=candidates,
    )
    _log_runbook_event(
        "compatible_targets.completed",
        source_record_id=source_record_id,
        search_name=search_name,
        target_count=response.count,
        scan_limit=scan_limit,
        duration_ms=max(0, round((time.perf_counter() - started) * 1000)),
    )
    return response


async def record_runbook_approval(
    settings: Settings,
    record_id: int,
    body: RunbookApprovalBody,
) -> RunbookApproval:
    started = time.perf_counter()
    _log_runbook_event(
        "approval.requested",
        source_record_id=record_id,
        runbook_id=body.runbook_id,
        decision=body.decision,
    )
    _ensure_feature_enabled(settings)
    if not splunk_store_configured(settings):
        raise VerifiedRunbookError(
            "PostgreSQL store not configured; set TSOC_POSTGRES_DSN.",
            status_code=503,
        )
    source = await get_stored_event_by_id(settings, record_id)
    if source is None:
        raise VerifiedRunbookError("Record not found", status_code=404)
    draft = await _latest_draft(settings, record_id)
    if draft is None or draft.runbook_id != body.runbook_id:
        raise VerifiedRunbookError(
            "Approval must reference the latest runbook draft."
        )
    if draft.status != "SOURCE_VERIFIED":
        raise VerifiedRunbookError(
            "Only a SOURCE_VERIFIED runbook can be approved or rejected."
        )
    approval = RunbookApproval(
        runbook_id=draft.runbook_id,
        source_record_id=record_id,
        decision=body.decision,
        analyst=body.analyst.strip() or "analyst",
        note=(body.note or "").strip() or None,
        created_at=_utc_now(),
    )
    await _persist_model(
        settings,
        record_type=RUNBOOK_APPROVAL_RECORD_TYPE,
        anchor=source,
        model=approval,
    )
    _log_runbook_event(
        "approval.completed",
        source_record_id=record_id,
        runbook_id=approval.runbook_id,
        decision=approval.decision,
        duration_ms=max(0, round((time.perf_counter() - started) * 1000)),
    )
    return approval


async def build_safe_response_preview(
    settings: Settings,
    record_id: int,
    body: SafeResponsePreviewBody,
) -> SafeResponsePreview:
    """Generate a policy-bounded manual response preview without executing anything."""
    started = time.perf_counter()
    _log_runbook_event(
        "response_preview.requested",
        source_record_id=record_id,
        runbook_id=body.runbook_id,
    )
    _ensure_feature_enabled(settings)
    _ensure_response_preview_runtime(settings)
    source = await _get_source_record(settings, record_id)
    draft = await _latest_draft(settings, record_id)
    if draft is None or draft.runbook_id != body.runbook_id:
        raise VerifiedRunbookError(
            "Response Preview must reference the latest runbook draft."
        )
    if draft.status not in ("PARSER_VALID", "SOURCE_VERIFIED"):
        raise VerifiedRunbookError(
            "Response Preview requires a PARSER_VALID or SOURCE_VERIFIED runbook."
        )

    evidence_basis = (
        "SOURCE_EVIDENCE" if draft.status == "SOURCE_VERIFIED" else "ANALYSIS_ONLY"
    )
    allowed_action_types = (
        _ALL_RESPONSE_TYPES
        if evidence_basis == "SOURCE_EVIDENCE"
        else _NON_DISRUPTIVE_RESPONSE_TYPES
    )
    prompt = _RESPONSE_PROMPT_PATH.read_text(encoding="utf-8")
    request_context = {
        **_minimized_source_snapshot(source),
        "runbook": _portable_runbook(draft).model_dump(mode="json"),
        "response_policy": {
            "evidence_basis": evidence_basis,
            "allowed_action_types": sorted(allowed_action_types),
            "execution_mode": "PREVIEW_ONLY",
            "human_approval_required": True,
            "commands_queries_scripts_forbidden": True,
        },
    }
    max_tokens = min(4096, settings.litellm_analysis_max_tokens)
    try:
        output = await litellm_chat_completion(
            settings,
            [
                {"role": "system", "content": prompt},
                {
                    "role": "user",
                    "content": json.dumps(
                        request_context,
                        ensure_ascii=False,
                        separators=(",", ":"),
                        default=str,
                    ),
                },
            ],
            temperature=0.1,
            max_tokens=max_tokens,
        )
        generated = _parse_safe_response_payload(
            output,
            allowed_action_types=allowed_action_types,
        )
    except Exception as exc:
        _log_runbook_event(
            "response_preview.generation_failed",
            level=logging.WARNING,
            source_record_id=record_id,
            runbook_id=draft.runbook_id,
            error_type=type(exc).__name__,
            duration_ms=max(0, round((time.perf_counter() - started) * 1000)),
        )
        raise

    duration_ms = max(0, round((time.perf_counter() - started) * 1000))
    usage = output.get("usage") if isinstance(output.get("usage"), dict) else {}
    preview = SafeResponsePreview(
        preview_id=str(uuid4()),
        runbook_id=draft.runbook_id,
        source_record_id=record_id,
        source_verdict=draft.source_verdict,
        evidence_basis=evidence_basis,
        actions=generated.actions,
        decision_summary=generated.decision_summary,
        limitations=generated.limitations,
        configured_model=str(settings.litellm_model or ""),
        model=str(output.get("model") or settings.litellm_model),
        prompt_tokens=usage.get("prompt_tokens"),
        completion_tokens=usage.get("completion_tokens"),
        generation_duration_ms=duration_ms,
        created_at=_utc_now(),
    )
    await _persist_model(
        settings,
        record_type=RUNBOOK_RESPONSE_PREVIEW_RECORD_TYPE,
        anchor=source,
        model=preview,
    )
    _log_runbook_event(
        "response_preview.completed",
        source_record_id=record_id,
        runbook_id=draft.runbook_id,
        preview_id=preview.preview_id,
        evidence_basis=preview.evidence_basis,
        action_count=len(preview.actions),
        execution_supported=preview.execution_supported,
        duration_ms=duration_ms,
    )
    return preview


async def record_safe_response_decision(
    settings: Settings,
    record_id: int,
    body: SafeResponseDecisionBody,
) -> SafeResponseDecision:
    """Approve a preview for manual handling or reject it; never execute it."""
    started = time.perf_counter()
    _log_runbook_event(
        "response_decision.requested",
        source_record_id=record_id,
        preview_id=body.preview_id,
        decision=body.decision,
    )
    _ensure_feature_enabled(settings)
    if not splunk_store_configured(settings):
        raise VerifiedRunbookError(
            "PostgreSQL store not configured; set TSOC_POSTGRES_DSN.",
            status_code=503,
        )
    source = await get_stored_event_by_id(settings, record_id)
    if source is None:
        raise VerifiedRunbookError("Record not found", status_code=404)
    draft = await _latest_draft(settings, record_id)
    preview = await _latest_response_preview(
        settings,
        record_id,
        draft.runbook_id if draft else None,
    )
    if preview is None or preview.preview_id != body.preview_id:
        raise VerifiedRunbookError(
            "Decision must reference the latest Response Preview for the latest runbook."
        )
    note = (body.note or "").strip() or None
    if body.decision == "approve_for_manual_action" and not note:
        raise VerifiedRunbookError(
            "Approval for manual action requires an analyst note describing the review."
        )
    decision = SafeResponseDecision(
        preview_id=preview.preview_id,
        runbook_id=preview.runbook_id,
        source_record_id=record_id,
        decision=body.decision,
        analyst=body.analyst.strip() or "analyst",
        note=note,
        created_at=_utc_now(),
    )
    await _persist_model(
        settings,
        record_type=RUNBOOK_RESPONSE_DECISION_RECORD_TYPE,
        anchor=source,
        model=decision,
    )
    _log_runbook_event(
        "response_decision.completed",
        source_record_id=record_id,
        runbook_id=preview.runbook_id,
        preview_id=preview.preview_id,
        decision=decision.decision,
        automatic_execution_performed=decision.automatic_execution_performed,
        duration_ms=max(0, round((time.perf_counter() - started) * 1000)),
    )
    return decision


async def run_shadow_replay(
    settings: Settings,
    target_record_id: int,
    body: RunbookShadowBody,
) -> RunbookShadowRun:
    """Execute an unapproved draft read-only on a distinct historical SID."""
    operation_started = time.perf_counter()
    _log_runbook_event(
        "shadow.requested",
        source_record_id=body.source_record_id,
        target_record_id=target_record_id,
        runbook_id=body.runbook_id,
        estimated_manual_minutes=body.estimated_manual_minutes,
    )
    _ensure_feature_enabled(settings)
    _ensure_runtime(settings)
    source = await get_stored_event_by_id(settings, body.source_record_id)
    if source is None:
        raise VerifiedRunbookError("Source record not found", status_code=404)
    target = await get_stored_event_by_id(settings, target_record_id)
    if target is None:
        raise VerifiedRunbookError("Target record not found", status_code=404)
    if str(source.get("tsoc_record_type") or "") != "soc_analysis":
        raise VerifiedRunbookError("The source must be a stored soc_analysis record.")
    if str(target.get("tsoc_record_type") or "") != "soc_analysis":
        raise VerifiedRunbookError("The target must be a stored soc_analysis record.")
    if target_record_id == body.source_record_id:
        raise VerifiedRunbookError("Shadow Replay requires a different target investigation.")

    source_sid = str(source.get("sid") or "").strip()
    target_sid = str(target.get("sid") or "").strip()
    if source_sid and target_sid == source_sid:
        raise VerifiedRunbookError(
            "Shadow Replay requires a target with a different Splunk SID."
        )
    draft = await _draft_by_id(settings, body.runbook_id)
    if draft is None:
        raise VerifiedRunbookError("Runbook not found.", status_code=404)
    if draft.source_record_id != body.source_record_id:
        raise VerifiedRunbookError(
            "The selected runbook does not belong to the requested source record."
        )
    target_search_name = str(target.get("search_name") or "").strip()
    if target_search_name != draft.applicable_search_name:
        raise VerifiedRunbookError(
            "Target search_name is not compatible with this runbook."
        )

    _, _, target_input = _analysis_context(target)
    execution_started = time.perf_counter()
    results: List[InvestigationQuestionItem] = []
    failure_reason: Optional[str] = None
    _log_runbook_event(
        "shadow.execution_started",
        source_record_id=body.source_record_id,
        target_record_id=target_record_id,
        source_sid=source_sid,
        target_sid=target_sid,
        runbook_id=draft.runbook_id,
        search_name=target_search_name,
        step_count=len(draft.steps),
    )
    try:
        results = await _finalize_steps(
            settings,
            draft.source_verdict,
            [step.intent for step in draft.steps],
            max_items=len(draft.steps),
            normalized=_safe_alert_fields(target_input.get("alert_fields")),
            search_name=target_search_name,
            sid=target.get("sid"),
            splunk_results=[],
        )
    except Exception as exc:
        failure_reason = _safe_log_value(str(exc), limit=500) or type(exc).__name__
        _log_runbook_event(
            "shadow.execution_failed",
            level=logging.WARNING,
            source_record_id=body.source_record_id,
            target_record_id=target_record_id,
            runbook_id=draft.runbook_id,
            error_type=type(exc).__name__,
        )
    duration_ms = max(0, round((time.perf_counter() - execution_started) * 1000))
    parser_valid, successful, total_rows = _result_metrics(results)
    execution_errors = _execution_error_count(results) + (1 if failure_reason else 0)
    if failure_reason is None:
        failure_reason = _first_execution_error(results)
    derived = derive_run_status(results, expected_count=len(draft.steps))
    status = (
        "FAILED"
        if failure_reason or derived == "FAILED"
        else "EVIDENCE_FOUND"
        if derived == "REUSED"
        else "NO_EVIDENCE"
    )
    projected_minutes_saved, projected_labor_savings = _projected_savings(
        settings,
        duration_ms=duration_ms,
        estimated_manual_minutes=body.estimated_manual_minutes,
    )
    shadow = RunbookShadowRun(
        shadow_run_id=str(uuid4()),
        runbook_id=draft.runbook_id,
        source_record_id=body.source_record_id,
        target_record_id=target_record_id,
        source_sid=source_sid or None,
        target_sid=target_sid or None,
        search_name=target_search_name,
        status=status,
        results=results,
        duration_ms=duration_ms,
        estimated_manual_minutes=body.estimated_manual_minutes,
        projected_minutes_saved=projected_minutes_saved,
        projected_labor_savings_usd=projected_labor_savings,
        parser_valid_step_count=parser_valid,
        successful_step_count=successful,
        total_evidence_rows=total_rows,
        execution_error_count=execution_errors,
        failure_reason=failure_reason,
        created_at=_utc_now(),
    )
    await _persist_model(
        settings,
        record_type=RUNBOOK_SHADOW_RUN_RECORD_TYPE,
        anchor=target,
        model=shadow,
    )
    _log_runbook_event(
        "shadow.completed",
        shadow_run_id=shadow.shadow_run_id,
        source_record_id=body.source_record_id,
        target_record_id=target_record_id,
        runbook_id=shadow.runbook_id,
        status=shadow.status,
        parser_valid_step_count=parser_valid,
        successful_step_count=successful,
        total_evidence_rows=total_rows,
        execution_error_count=execution_errors,
        projected_minutes_saved=projected_minutes_saved,
        projected_labor_savings_usd=projected_labor_savings,
        duration_ms=max(0, round((time.perf_counter() - operation_started) * 1000)),
    )
    return shadow


async def run_verified_runbook(
    settings: Settings,
    target_record_id: int,
    body: RunbookRunBody,
) -> RunbookRun:
    operation_started = time.perf_counter()
    _log_runbook_event(
        "reuse.requested",
        source_record_id=body.source_record_id,
        target_record_id=target_record_id,
        runbook_id=body.runbook_id,
        estimated_manual_minutes=body.estimated_manual_minutes,
    )
    _ensure_feature_enabled(settings)
    _ensure_runtime(settings)
    source = await get_stored_event_by_id(settings, body.source_record_id)
    if source is None:
        raise VerifiedRunbookError("Source record not found", status_code=404)
    target = await get_stored_event_by_id(settings, target_record_id)
    if target is None:
        raise VerifiedRunbookError("Target record not found", status_code=404)
    if str(target.get("tsoc_record_type") or "") != "soc_analysis":
        raise VerifiedRunbookError("The target must be a stored soc_analysis record.")
    if target_record_id == body.source_record_id:
        raise VerifiedRunbookError("Reuse requires a different target investigation.")
    source_sid = str(source.get("sid") or "").strip()
    target_sid = str(target.get("sid") or "").strip()
    if source_sid and target_sid == source_sid:
        raise VerifiedRunbookError(
            "Reuse requires a target with a different Splunk SID."
        )

    draft = await _latest_draft(settings, body.source_record_id)
    if draft is None or draft.runbook_id != body.runbook_id:
        raise VerifiedRunbookError("The requested runbook is not the latest draft.")
    approval = await _latest_approval(
        settings,
        body.source_record_id,
        draft.runbook_id,
    )
    if approval is None or approval.decision != "approve":
        raise VerifiedRunbookError("The latest runbook draft has not been approved.")
    if str(target.get("search_name") or "") != draft.applicable_search_name:
        raise VerifiedRunbookError(
            "Target search_name is not compatible with this runbook."
        )

    _, _, target_input = _analysis_context(target)
    started = time.perf_counter()
    _log_runbook_event(
        "reuse.execution_started",
        source_record_id=body.source_record_id,
        target_record_id=target_record_id,
        runbook_id=draft.runbook_id,
        search_name=target.get("search_name"),
        step_count=len(draft.steps),
    )
    try:
        results = await _finalize_steps(
            settings,
            draft.source_verdict,
            [step.intent for step in draft.steps],
            max_items=len(draft.steps),
            normalized=_safe_alert_fields(target_input.get("alert_fields")),
            search_name=str(target.get("search_name") or ""),
            sid=target.get("sid"),
            splunk_results=[],
        )
    except Exception as exc:
        _log_runbook_event(
            "reuse.execution_failed",
            level=logging.WARNING,
            source_record_id=body.source_record_id,
            target_record_id=target_record_id,
            runbook_id=draft.runbook_id,
            duration_ms=max(0, round((time.perf_counter() - started) * 1000)),
            error_type=type(exc).__name__,
        )
        raise
    duration_ms = max(0, round((time.perf_counter() - started) * 1000))
    automated_minutes = duration_ms / 60_000.0
    estimated_minutes_saved = round(
        max(0.0, body.estimated_manual_minutes - automated_minutes),
        3,
    )
    _, successful, total_rows = _result_metrics(results)
    run_status = derive_run_status(results, expected_count=len(draft.steps))
    _log_runbook_event(
        "reuse.execution_completed",
        source_record_id=body.source_record_id,
        target_record_id=target_record_id,
        runbook_id=draft.runbook_id,
        status=run_status,
        step_count=len(draft.steps),
        successful_step_count=successful,
        total_evidence_rows=total_rows,
        duration_ms=duration_ms,
    )
    run = RunbookRun(
        runbook_id=draft.runbook_id,
        source_record_id=body.source_record_id,
        target_record_id=target_record_id,
        status=run_status,
        results=results,
        duration_ms=duration_ms,
        estimated_manual_minutes=body.estimated_manual_minutes,
        estimated_minutes_saved=estimated_minutes_saved,
        savings_percent=round(
            estimated_minutes_saved / body.estimated_manual_minutes * 100.0,
            2,
        ),
        successful_step_count=successful,
        total_evidence_rows=total_rows,
        created_at=_utc_now(),
    )
    await _persist_model(
        settings,
        record_type=RUNBOOK_RUN_RECORD_TYPE,
        anchor=target,
        model=run,
    )
    _log_runbook_event(
        "reuse.completed",
        source_record_id=body.source_record_id,
        target_record_id=target_record_id,
        runbook_id=run.runbook_id,
        status=run.status,
        estimated_minutes_saved=run.estimated_minutes_saved,
        savings_percent=run.savings_percent,
        duration_ms=max(0, round((time.perf_counter() - operation_started) * 1000)),
    )
    return run
