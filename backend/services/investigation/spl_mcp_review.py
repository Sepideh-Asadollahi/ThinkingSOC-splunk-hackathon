"""LLM review pass for SPL drafted by Splunk MCP (saia_generate_spl)."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from config import Settings
from models.analysis import RootCauseSpl, RootCauseSplValidation, SplSearchResult
from services.soc_analysis.soc_analysis_canonical import build_canonical_static_context
from services.soc_analysis_graph.llm import llm_json_response, spl_review_max_tokens
from services.soc_analysis.soc_analysis_prompts import load_prompt_file
from services.soc_analysis.soc_analysis_root_cause_spl import sanitize_root_cause_spl_output
from services.investigation.spl_tstats_sanitize import sanitize_spl_draft

logger = logging.getLogger(__name__)

_PROMPT_SPL_MCP_REVIEW = "prompt_spl_mcp_review_system.md"
_PROMPT_SPL_EXECUTION_REFINE = "prompt_spl_execution_refine_system.md"


def spl_validation_is_error(validation: Optional[RootCauseSplValidation]) -> bool:
    """True when Splunk parser reported a syntax/semantic SPL error."""
    if not isinstance(validation, RootCauseSplValidation):
        return False
    return validation.valid is False and bool((validation.message or "").strip())


def _spl_error_refine_max_attempts(settings: Settings) -> int:
    return max(0, min(3, int(getattr(settings, "tsoc_spl_execute_refine_max_attempts", 3) or 0)))


def _spl_error_refine_enabled(settings: Settings) -> bool:
    return bool(getattr(settings, "tsoc_spl_llm_refine_on_error", True))


def _review_user_message(
    *,
    canonical: str,
    draft: RootCauseSpl,
    objective: Optional[str],
    cim_schema_summary: str = "",
) -> str:
    validation_blob = ""
    if draft.validation is not None:
        validation_blob = json.dumps(
            draft.validation.model_dump(mode="json"),
            ensure_ascii=False,
        )
    draft_blob = json.dumps(
        {
            "spl": draft.spl,
            "explanation": draft.explanation,
            "time_window": draft.time_window,
            "pivots": draft.pivots,
            "notes": draft.notes,
        },
        ensure_ascii=False,
    )
    schema_block = ""
    if cim_schema_summary:
        schema_block = (
            "\n\n## CIM field paths (datamodelsimple — use exactly)\n"
            + cim_schema_summary
        )
    error_block = ""
    if spl_validation_is_error(draft.validation):
        error_block = (
            "\n\n## Splunk error (must fix)\n"
            + (draft.validation.message or "SPL validation failed")
        )
    return (
        "Review and correct the following SPL from Splunk AI Assistant (MCP). "
        "Return ONLY one JSON object (no markdown, no reasoning, no SPL prose).\n\n"
        "## System Context\n"
        + canonical
        + schema_block
        + error_block
        + "\n\n## Analyst objective\n"
        + (objective or "(none)")
        + "\n\n## Draft SPL (from saia_generate_spl)\n"
        + draft_blob
        + "\n\n## Splunk parser validation\n"
        + (validation_blob or "(not run)")
    )


async def review_spl_from_mcp_with_llm(
    settings: Settings,
    *,
    draft: RootCauseSpl,
    normalized: Dict[str, Any],
    search_name: Optional[str],
    sid: Optional[str],
    splunk_results: List[Dict[str, Any]],
    objective: Optional[str],
    enrichment: Optional[Dict[str, Any]] = None,
    cim_schema_summary: str = "",
    always_review: bool = False,
) -> tuple[RootCauseSpl, bool]:
    """
    Run analysis LLM over MCP-generated SPL to fix issues.

    Returns (possibly updated RootCauseSpl, reviewed_flag).
    """
    if not settings.tsoc_spl_llm_review and not always_review:
        return draft, False

    identity = enrichment or {
        "resolved_asset_id": None,
        "resolved_user_id": None,
        "matched_relationship_ids": [],
        "confidence": "low",
        "notes": "not provided for SPL review",
    }
    canonical = build_canonical_static_context(
        normalized=normalized,
        search_name=search_name,
        sid=sid,
        splunk_results_preview=(splunk_results or [])[:5],
        enrichment=identity,
        risk_context="",
        inventory_user=None,
        inventory_asset=None,
    )
    sys_p = load_prompt_file(_PROMPT_SPL_MCP_REVIEW)
    from services.llm.llm_context_budget import clamp_text, schema_prompt_max_chars

    schema_cap = schema_prompt_max_chars(settings)
    user = _review_user_message(
        canonical=canonical,
        draft=draft,
        objective=objective,
        cim_schema_summary=clamp_text(cim_schema_summary, schema_cap),
    )

    mt = spl_review_max_tokens(settings)
    try:
        llm_json = await llm_json_response(settings, sys_p, user, max_tokens=mt)
        reviewed = sanitize_root_cause_spl_output(llm_json)
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("spl mcp llm review JSON parse failed, retrying: %s", e)
        try:
            retry_user = (
                user
                + "\n\nIMPORTANT: Output ONLY valid JSON with keys "
                "spl, explanation, time_window, pivots, notes. "
                "No chain-of-thought, no markdown fences, no SPL discussion."
            )
            llm_json = await llm_json_response(settings, sys_p, retry_user, max_tokens=mt)
            reviewed = sanitize_root_cause_spl_output(llm_json)
        except Exception as retry_e:
            logger.warning(
                "spl mcp llm review failed, keeping MCP draft: %s", retry_e
            )
            return draft, False
    except Exception as e:
        logger.warning("spl mcp llm review failed, keeping MCP draft: %s", e)
        return draft, False

    if reviewed is None or not reviewed.spl:
        return draft, False

    reviewed.spl = sanitize_spl_draft(reviewed.spl or "")
    if not reviewed.spl:
        return draft, False

    notes = list(reviewed.notes or [])
    if "llm_reviewed_after_mcp_saia" not in notes:
        notes.append("llm_reviewed_after_mcp_saia")
    reviewed.notes = notes
    if not reviewed.explanation:
        reviewed.explanation = draft.explanation
    return reviewed, True


def _execution_feedback_message(result: Optional[SplSearchResult]) -> str:
    if result is None:
        return "No execution result (Splunk REST may be unavailable)."
    if result.error:
        return "Splunk error: {0}".format(result.error)
    if (result.row_count or 0) == 0:
        return "Splunk returned 0 rows (query ran but no matching events in the time window)."
    return "Unexpected refine trigger (rows={0}).".format(result.row_count)


def _spl_error_refine_user_message(
    *,
    canonical: str,
    draft: RootCauseSpl,
    objective: Optional[str],
    error_message: str,
    error_source: str,
    result: Optional[SplSearchResult] = None,
    attempt: int = 1,
    cim_schema_summary: str = "",
    splunk_catalog: str = "",
) -> str:
    validation_blob = ""
    if draft.validation is not None:
        validation_blob = json.dumps(
            draft.validation.model_dump(mode="json"),
            ensure_ascii=False,
        )
    draft_blob = json.dumps(
        {
            "spl": draft.spl,
            "explanation": draft.explanation,
            "time_window": draft.time_window,
            "pivots": draft.pivots,
            "notes": draft.notes,
        },
        ensure_ascii=False,
    )
    exec_blob = ""
    if result is not None:
        exec_blob = json.dumps(
            {
                "row_count": result.row_count,
                "error": result.error,
                "truncated": result.truncated,
                "sample_rows": (result.rows or [])[:3],
            },
            ensure_ascii=False,
            default=str,
        )
    schema_block = ""
    if cim_schema_summary:
        schema_block = (
            "\n\n## CIM field paths (datamodelsimple — use exactly)\n"
            + cim_schema_summary
        )
    catalog_block = splunk_catalog or ""
    exec_summary = ""
    if result is not None:
        exec_summary = _execution_feedback_message(result)
    return (
        "Refine attempt {0}. Fix the SPL using the Splunk error below.\n\n"
        "## System Context\n{1}{2}{3}\n\n"
        "## Investigation question\n{4}\n\n"
        "## Current SPL\n{5}\n\n"
        "## Splunk error (must fix)\nSource: {6}\n{7}\n\n"
        "## Parser validation\n{8}\n\n"
        "## Splunk execution result\n{9}\n\n"
        "## Execution summary\n{10}"
    ).format(
        attempt,
        canonical,
        schema_block,
        catalog_block,
        objective or "(none)",
        draft_blob,
        error_source,
        error_message,
        validation_blob or "(not run)",
        exec_blob or "(none)",
        exec_summary or "(n/a)",
    )


def _execution_refine_user_message(
    *,
    canonical: str,
    draft: RootCauseSpl,
    objective: Optional[str],
    result: Optional[SplSearchResult],
    attempt: int,
) -> str:
    validation_blob = ""
    if draft.validation is not None:
        validation_blob = json.dumps(
            draft.validation.model_dump(mode="json"),
            ensure_ascii=False,
        )
    draft_blob = json.dumps(
        {
            "spl": draft.spl,
            "explanation": draft.explanation,
            "time_window": draft.time_window,
            "pivots": draft.pivots,
            "notes": draft.notes,
        },
        ensure_ascii=False,
    )
    exec_blob = ""
    if result is not None:
        exec_blob = json.dumps(
            {
                "row_count": result.row_count,
                "error": result.error,
                "truncated": result.truncated,
                "sample_rows": (result.rows or [])[:3],
            },
            ensure_ascii=False,
            default=str,
        )
    return (
        "Refine attempt {0}. Fix the SPL using execution feedback.\n\n"
        "## System Context\n{1}\n\n"
        "## Investigation question\n{2}\n\n"
        "## Current SPL\n{3}\n\n"
        "## Parser validation\n{4}\n\n"
        "## Splunk execution result\n{5}\n\n"
        "## Execution summary\n{6}"
    ).format(
        attempt,
        canonical,
        objective or "(none)",
        draft_blob,
        validation_blob or "(not run)",
        exec_blob or "(none)",
        _execution_feedback_message(result),
    )


async def _splunk_catalog_block(
    settings: Settings,
    *,
    normalized: Dict[str, Any],
    search_name: Optional[str],
    splunk_results: List[Dict[str, Any]],
) -> str:
    """Live index/source/sourcetype names from Splunk MCP (no hardcoded catalog)."""
    from config import mcp_configured
    from splunk.mcp.context_builder import build_mcp_alert_context

    if not mcp_configured(settings):
        return ""
    try:
        ctx = await build_mcp_alert_context(
            settings,
            normalized=normalized or {},
            search_name=search_name,
            splunk_results=splunk_results or [],
        )
    except Exception as e:
        logger.debug("splunk catalog for refine skipped: %s", e)
        return ""
    if ctx is None:
        return ""
    parts: List[str] = []
    if ctx.indexes:
        parts.append("indexes: " + ", ".join(ctx.indexes[:40]))
    if ctx.metadata_sourcetypes:
        parts.append("sourcetypes: " + ", ".join(ctx.metadata_sourcetypes[:25]))
    if ctx.metadata_sources:
        parts.append("sources: " + ", ".join(ctx.metadata_sources[:25]))
    if not parts:
        return ""
    return (
        "\n\n## Splunk catalog (pick exact names from this deployment)\n"
        + "\n".join(parts)
    )


async def refine_spl_with_llm_on_error(
    settings: Settings,
    *,
    draft: RootCauseSpl,
    error_message: str,
    error_source: str = "splunk",
    normalized: Dict[str, Any],
    search_name: Optional[str],
    sid: Optional[str],
    splunk_results: List[Dict[str, Any]],
    objective: Optional[str],
    execution_result: Optional[SplSearchResult] = None,
    attempt: int = 1,
    enrichment: Optional[Dict[str, Any]] = None,
    cim_schema_summary: str = "",
    note_tag: Optional[str] = None,
) -> tuple[RootCauseSpl, bool]:
    """LiteLLM pass: Splunk error text → corrected SPL JSON."""
    if not _spl_error_refine_enabled(settings):
        return draft, False
    if not (error_message or "").strip():
        return draft, False

    identity = enrichment or {
        "resolved_asset_id": None,
        "resolved_user_id": None,
        "matched_relationship_ids": [],
        "confidence": "low",
        "notes": "not provided for SPL error refine",
    }
    canonical = build_canonical_static_context(
        normalized=normalized,
        search_name=search_name,
        sid=sid,
        splunk_results_preview=(splunk_results or [])[:5],
        enrichment=identity,
        risk_context="",
        inventory_user=None,
        inventory_asset=None,
    )
    sys_p = load_prompt_file(_PROMPT_SPL_EXECUTION_REFINE)
    catalog = await _splunk_catalog_block(
        settings,
        normalized=normalized,
        search_name=search_name,
        splunk_results=splunk_results,
    )
    user = _spl_error_refine_user_message(
        canonical=canonical,
        draft=draft,
        objective=objective,
        error_message=error_message.strip(),
        error_source=error_source,
        result=execution_result,
        attempt=attempt,
        cim_schema_summary=cim_schema_summary,
        splunk_catalog=catalog,
    )
    try:
        llm_json = await llm_json_response(
            settings,
            sys_p,
            user,
            max_tokens=spl_review_max_tokens(settings),
        )
        reviewed = sanitize_root_cause_spl_output(llm_json)
    except Exception as e:
        logger.warning("spl llm refine on error failed: %s", e)
        return draft, False

    if reviewed is None or not reviewed.spl:
        return draft, False

    reviewed.spl = sanitize_spl_draft(reviewed.spl or "")
    if not reviewed.spl:
        return draft, False

    notes = list(reviewed.notes or [])
    tag = note_tag or "llm_refine_after_error_{0}".format(attempt)
    if tag not in notes:
        notes.append(tag)
    reviewed.notes = notes
    if not reviewed.explanation:
        reviewed.explanation = draft.explanation
    return reviewed, True


async def refine_root_cause_spl_until_valid(
    settings: Settings,
    rc: RootCauseSpl,
    *,
    normalized: Dict[str, Any],
    search_name: Optional[str] = None,
    sid: Optional[str] = None,
    splunk_results: Optional[List[Dict[str, Any]]] = None,
    objective: Optional[str] = None,
    cim_schema_summary: str = "",
    enrichment: Optional[Dict[str, Any]] = None,
    max_attempts: Optional[int] = None,
    normalize_tstats: bool = False,
) -> tuple[RootCauseSpl, bool]:
    """Re-validate after each LLM fix until parser accepts SPL or attempts exhausted."""
    from services.soc_analysis.soc_analysis_root_cause_spl import validate_root_cause_spl
    from services.investigation.spl_tstats_sanitize import normalize_tstats_spl, sanitize_spl_draft

    if not _spl_error_refine_enabled(settings):
        return rc, False

    limit = _spl_error_refine_max_attempts(settings) if max_attempts is None else max(
        0, min(3, int(max_attempts))
    )
    any_fixed = False
    rows = splunk_results or []

    for attempt in range(1, limit + 1):
        if not spl_validation_is_error(rc.validation):
            break
        msg = (rc.validation.message or "SPL validation failed").strip()
        source = rc.validation.method or "splunk_parser"
        rc, fixed = await refine_spl_with_llm_on_error(
            settings,
            draft=rc,
            error_message=msg,
            error_source=source,
            normalized=normalized,
            search_name=search_name,
            sid=sid,
            splunk_results=rows,
            objective=objective,
            attempt=attempt,
            enrichment=enrichment,
            cim_schema_summary=cim_schema_summary,
            note_tag="llm_refine_after_parser_error_{0}".format(attempt),
        )
        if not fixed:
            break
        any_fixed = True
        rc.spl = (
            normalize_tstats_spl(rc.spl or "")
            if normalize_tstats
            else sanitize_spl_draft(rc.spl or "")
        )
        rc.validation = await validate_root_cause_spl(
            settings, rc, normalize_tstats=normalize_tstats
        )

    return rc, any_fixed


async def review_spl_after_execution_with_llm(
    settings: Settings,
    *,
    draft: RootCauseSpl,
    normalized: Dict[str, Any],
    search_name: Optional[str],
    sid: Optional[str],
    splunk_results: List[Dict[str, Any]],
    objective: Optional[str],
    execution_result: Optional[SplSearchResult],
    attempt: int = 1,
    enrichment: Optional[Dict[str, Any]] = None,
) -> tuple[RootCauseSpl, bool]:
    """LiteLLM pass to fix SPL after oneshot error or zero rows."""
    err = _execution_feedback_message(execution_result)
    reviewed, ok = await refine_spl_with_llm_on_error(
        settings,
        draft=draft,
        error_message=err,
        error_source="splunk_execute",
        normalized=normalized,
        search_name=search_name,
        sid=sid,
        splunk_results=splunk_results,
        objective=objective,
        execution_result=execution_result,
        attempt=attempt,
        enrichment=enrichment,
        note_tag="llm_refine_after_execute_{0}".format(attempt),
    )
    return reviewed, ok
