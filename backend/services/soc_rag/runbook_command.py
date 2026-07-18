"""Natural-language Chat command for safe reuse of an approved Runbook by SID."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Optional, Sequence

from config import Settings
from models.runbook import RunbookRunBody
from services.investigation.verified_runbook import (
    VerifiedRunbookError,
    list_runbook_library,
    run_verified_runbook,
)
from services.splunk_json_store import search_stored_events

from .models import SocChatCitation

logger = logging.getLogger(__name__)

_RUNBOOK_RE = re.compile(
    r"(?:\brun\s*book\b|\bplaybook\b)",
    re.IGNORECASE,
)
_SID_MARKER_RE = re.compile(
    r"\bS\.?I\.?D\.?\b\s*(?:[:=#]|is)?\s*[`\"']?"
    r"([A-Za-z0-9][A-Za-z0-9._:@/\-]{0,254})",
    re.IGNORECASE,
)
_EXECUTE_RE = re.compile(
    r"(?:\b(?:please\s+)?(?:run|execute|apply|launch|start)\b|"
    r"\bcan\s+you\s+(?:run|execute|apply)\b)",
    re.IGNORECASE,
)
_NEGATED_RE = re.compile(
    r"(?:"
    r"\bdo\s+not\s+(?:run|execute|apply)\b|\bdon['’]?t\s+(?:run|execute|apply)\b|"
    r"\bwithout\s+(?:running|executing)\b|\bdry[ -]?run\b"
    r")",
    re.IGNORECASE,
)
_TRAILING_SID_PUNCTUATION = ".,;!?)]}>"


def _normalize_text(value: str) -> str:
    return str(value or "").strip()


def _unique(values: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        cleaned = value.strip("`\"'").rstrip(_TRAILING_SID_PUNCTUATION)
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        result.append(cleaned)
    return tuple(result)


@dataclass(frozen=True)
class RunbookExecutionIntent:
    detected: bool
    sid: Optional[str] = None
    sid_candidates: tuple[str, ...] = ()
    language: str = "en"
    reason: str = "not_a_runbook_command"


@dataclass
class RunbookChatCommandResult:
    answer: str
    metadata: Dict[str, Any]
    citations: list[SocChatCitation] = field(default_factory=list)


def detect_runbook_execution_intent(
    message: str,
    *,
    prior_messages: Optional[Sequence[Dict[str, str]]] = None,
) -> RunbookExecutionIntent:
    """Recognize an explicit execute request without delegating authority to an LLM."""
    text = _normalize_text(message)
    language = "en"
    if not text or _NEGATED_RE.search(text):
        return RunbookExecutionIntent(False, language=language, reason="negated_or_empty")

    execute_requested = bool(_EXECUTE_RE.search(text))
    if not execute_requested:
        return RunbookExecutionIntent(False, language=language, reason="no_execute_request")

    has_runbook_context = bool(_RUNBOOK_RE.search(text))
    if not has_runbook_context:
        for item in list(prior_messages or ())[-4:]:
            if _RUNBOOK_RE.search(_normalize_text(item.get("content") or "")):
                has_runbook_context = True
                break
    if not has_runbook_context:
        return RunbookExecutionIntent(False, language=language, reason="no_runbook_context")

    candidates = _unique(match.group(1) for match in _SID_MARKER_RE.finditer(text))
    if len(candidates) == 1:
        return RunbookExecutionIntent(
            True,
            sid=candidates[0],
            sid_candidates=candidates,
            language=language,
            reason="ready",
        )
    return RunbookExecutionIntent(
        True,
        sid=None,
        sid_candidates=candidates,
        language=language,
        reason="multiple_sids" if len(candidates) > 1 else "missing_sid",
    )


def _result(
    intent: RunbookExecutionIntent,
    *,
    status: str,
    answer: str,
    metadata: Optional[Dict[str, Any]] = None,
    citations: Optional[list[SocChatCitation]] = None,
) -> RunbookChatCommandResult:
    return RunbookChatCommandResult(
        answer=answer,
        metadata={
            "query_mode": "runbook_execute",
            "command_detected": True,
            "status": status,
            "sid": intent.sid,
            **(metadata or {}),
        },
        citations=citations or [],
    )


def _pick_target(rows: Sequence[Dict[str, Any]], sid: str) -> tuple[Optional[Dict[str, Any]], list[str]]:
    exact = [row for row in rows if str(row.get("sid") or "") == sid]
    if exact:
        return exact[0], []
    distinct_sids = list(dict.fromkeys(str(row.get("sid") or "") for row in rows if row.get("sid")))
    if len(distinct_sids) == 1:
        return rows[0], []
    return None, distinct_sids


async def execute_runbook_chat_command(
    settings: Settings,
    intent: RunbookExecutionIntent,
    *,
    request_id: str = "-",
) -> RunbookChatCommandResult:
    """Resolve SID → analysis → latest approved exact-name Runbook → guarded reuse."""
    if not intent.sid:
        if intent.reason == "multiple_sids":
            values = ", ".join(f"`{item}`" for item in intent.sid_candidates)
            return _result(
                intent,
                status="NEEDS_ONE_SID",
                answer=f"I found multiple SIDs ({values}). Specify exactly one SID so the wrong Runbook is not run.",
            )
        return _result(
            intent,
            status="NEEDS_SID",
            answer="Include the SID explicitly, for example: `Run the approved Runbook for SID demo-123`.",
        )

    logger.info("soc_chat runbook_command.resolve rid=%s sid=%s", request_id, intent.sid)
    rows = await search_stored_events(
        settings,
        job_sid=intent.sid,
        record_type="soc_analysis",
        limit=100,
        order="desc",
    )
    if not rows:
        return _result(
            intent,
            status="TARGET_NOT_FOUND",
            answer=f"No stored SOC analysis was found for SID `{intent.sid}`. Ingest and analyze that alert first.",
        )

    target, alternatives = _pick_target(rows, intent.sid)
    if target is None:
        values = ", ".join(f"`{item}`" for item in alternatives[:10])
        return _result(
            intent,
            status="AMBIGUOUS_TARGET",
            answer=f"That SID maps to multiple alert rows: {values}. Specify one exact row SID.",
            metadata={"candidate_sids": alternatives[:10]},
        )

    target_id = int(target["id"])
    target_sid = str(target.get("sid") or intent.sid)
    search_name = str(target.get("search_name") or "").strip()
    if not search_name:
        return _result(
            intent,
            status="MISSING_ALERT_NAME",
            answer=f"The analysis for SID `{target_sid}` has no Alert Name, so safe exact Runbook matching is not possible.",
            metadata={"target_record_id": target_id, "target_sid": target_sid},
        )

    library = await list_runbook_library(settings, search_name=search_name)
    candidates = []
    for group in library.groups:
        for item in group.runbooks:
            draft = item.draft
            approved = item.latest_approval is not None and item.latest_approval.decision == "approve"
            different_target = draft.source_record_id > 0 and draft.source_record_id != target_id
            if (
                item.is_latest_for_source
                and approved
                and different_target
                and draft.status == "SOURCE_VERIFIED"
                and draft.applicable_search_name == search_name
            ):
                candidates.append(item)

    if not candidates:
        return _result(
            intent,
            status="NO_APPROVED_RUNBOOK",
            answer=(
                f"No approved SOURCE_VERIFIED Runbook with a different source was found for **{search_name}**. "
                "Review it in ThinkingSOC Lite and record Human Approval first."
            ),
            metadata={"target_record_id": target_id, "target_sid": target_sid, "search_name": search_name},
        )

    selected = max(
        candidates,
        key=lambda item: (str(item.draft.created_at or ""), int(item.draft.revision or 0)),
    )
    draft = selected.draft
    body = RunbookRunBody(
        source_record_id=draft.source_record_id,
        runbook_id=draft.runbook_id,
        estimated_manual_minutes=settings.tsoc_runbook_default_manual_minutes,
    )
    logger.info(
        "soc_chat runbook_command.execute rid=%s sid=%s target_record_id=%d source_record_id=%d runbook_id=%s",
        request_id,
        target_sid,
        target_id,
        draft.source_record_id,
        draft.runbook_id,
    )
    try:
        run = await run_verified_runbook(settings, target_id, body)
    except VerifiedRunbookError as exc:
        logger.warning(
            "soc_chat runbook_command.blocked rid=%s sid=%s target_record_id=%d error=%s",
            request_id,
            target_sid,
            target_id,
            exc,
        )
        return _result(
            intent,
            status="BLOCKED",
            answer=f"The Runbook was not run for SID `{target_sid}`: {exc}",
            metadata={
                "target_record_id": target_id,
                "target_sid": target_sid,
                "search_name": search_name,
                "runbook_id": draft.runbook_id,
                "source_record_id": draft.source_record_id,
            },
        )
    except Exception as exc:
        logger.exception(
            "soc_chat runbook_command.failed rid=%s sid=%s target_record_id=%d error_type=%s",
            request_id,
            target_sid,
            target_id,
            type(exc).__name__,
        )
        return _result(
            intent,
            status="FAILED",
            answer=f"Runbook execution for SID `{target_sid}` did not complete because a tool or service failed. Check the Runbook log and retry.",
            metadata={
                "target_record_id": target_id,
                "target_sid": target_sid,
                "search_name": search_name,
                "runbook_id": draft.runbook_id,
                "source_record_id": draft.source_record_id,
                "error_type": type(exc).__name__,
            },
        )

    status = run.status
    answer = (
        "### Runbook execution completed\n\n"
        f"- **Target SID:** `{target_sid}`\n"
        f"- **Alert Name:** {search_name}\n"
        f"- **Runbook:** {draft.title} (`{draft.runbook_id}`)\n"
        f"- **Status:** **{status}**\n"
        f"- **Successful steps:** {run.successful_step_count} of {len(draft.steps)}\n"
        f"- **Evidence rows:** {run.total_evidence_rows}\n"
        f"- **Duration:** {run.duration_ms} ms\n\n"
        "This performed read-only investigation steps only; no containment or automatic operational change was executed."
    )
    citation = SocChatCitation(
        doc_id=f"runbook_run:{draft.runbook_id}:{target_id}",
        sid=target_sid,
        search_name=search_name,
        summary_line=f"{draft.title} — {status}",
        doc_type="runbook_run",
        similarity_score=1.0,
    )
    logger.info(
        "soc_chat runbook_command.completed rid=%s sid=%s target_record_id=%d runbook_id=%s status=%s",
        request_id,
        target_sid,
        target_id,
        draft.runbook_id,
        status,
    )
    return _result(
        intent,
        status=status,
        answer=answer,
        metadata={
            "target_record_id": target_id,
            "target_sid": target_sid,
            "search_name": search_name,
            "runbook_id": draft.runbook_id,
            "source_record_id": draft.source_record_id,
            "successful_step_count": run.successful_step_count,
            "step_count": len(draft.steps),
            "total_evidence_rows": run.total_evidence_rows,
            "duration_ms": run.duration_ms,
            "automatic_response_executed": False,
        },
        citations=[citation],
    )
