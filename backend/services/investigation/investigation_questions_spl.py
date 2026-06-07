"""Normalize investigation questions + per-question SPL for SOC analysis output."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from config import Settings, investigation_questions_max
from models.analysis import InvestigationQuestionItem, RootCauseSpl, RootCauseSplValidation
from services.investigation.investigation_spl_execute import (
    execute_investigation_item,
    needs_spl_execution_refine,
)
from services.soc_analysis.soc_analysis_prompts import load_root_cause_spl_system_prompt
from services.soc_analysis.soc_analysis_root_cause_spl import (
    build_rule_based_root_cause_spl,
    build_zero_row_fallback_spl,
    investigation_question_spl_user_message,
    root_cause_spl_user_message,
    sanitize_root_cause_spl_output,
    validate_root_cause_spl,
)
from services.soc_analysis.soc_verdict import verdict_implies_false_positive
from services.investigation.spl_mcp_review import (
    refine_root_cause_spl_until_valid,
    review_spl_after_execution_with_llm,
    spl_validation_is_error,
)
from services.investigation.spl_results_analysis import analyze_spl_execution_results_with_llm
from services.investigation.spl_saia_analysis import enrich_investigation_item_with_saia
from services.investigation.spl_predict_pipeline import (
    SPL_ALL_TIME_WINDOW,
    normalize_execution_time_window,
    build_predict_prompt,
    generate_spl_via_predict,
)
from services.investigation.spl_tstats_sanitize import sanitize_spl_draft
from splunk.client import SplunkRestClient

logger = logging.getLogger(__name__)


def _item_from_question_and_spl(
    question: str,
    spl_payload: Any,
    *,
    fallback_rc: Optional[RootCauseSpl] = None,
) -> Optional[InvestigationQuestionItem]:
    q = str(question or "").strip()
    if not q:
        return None

    rc: Optional[RootCauseSpl] = None
    if isinstance(spl_payload, dict):
        rc = sanitize_root_cause_spl_output(spl_payload)
    elif isinstance(spl_payload, RootCauseSpl):
        rc = spl_payload

    if rc is None or not rc.spl:
        rc = fallback_rc or build_rule_based_root_cause_spl({})

    if not rc.spl:
        return None

    return InvestigationQuestionItem(
        question=q,
        spl=rc.spl,
        explanation=rc.explanation,
        time_window=rc.time_window,
        pivots=list(rc.pivots),
        notes=list(rc.notes),
        validation=rc.validation,
    )


def sanitize_investigation_question_items(
    raw: Any,
    *,
    legacy_root_spl: Any = None,
    normalized: Optional[Dict[str, Any]] = None,
    max_items: int = 3,
) -> List[InvestigationQuestionItem]:
    """Parse LLM / stored payloads into question+SPL pairs (supports legacy string lists)."""
    fallback_rc = build_rule_based_root_cause_spl(normalized or {})
    legacy_rc = sanitize_root_cause_spl_output(legacy_root_spl) if legacy_root_spl else None

    if raw is None:
        raw = []

    out: List[InvestigationQuestionItem] = []

    if isinstance(raw, list):
        for entry in raw:
            if isinstance(entry, InvestigationQuestionItem):
                if entry.question and entry.spl and not any(x.question == entry.question for x in out):
                    out.append(entry)
                if len(out) >= max_items:
                    break
                continue
            if isinstance(entry, str):
                item = _item_from_question_and_spl(entry, None, fallback_rc=legacy_rc or fallback_rc)
            elif isinstance(entry, dict):
                q = str(entry.get("question") or entry.get("text") or "").strip()
                spl_part = entry if entry.get("spl") else entry
                item = _item_from_question_and_spl(
                    q,
                    spl_part,
                    fallback_rc=legacy_rc or fallback_rc,
                )
            else:
                item = None
            if item and not any(x.question == item.question for x in out):
                out.append(item)
            if len(out) >= max_items:
                break

    if not out and legacy_rc and legacy_rc.spl:
        item = _item_from_question_and_spl(
            "Run root-cause SPL for this alert context.",
            legacy_rc,
            fallback_rc=fallback_rc,
        )
        if item:
            out.append(item)

    return out


async def validate_investigation_question_items(
    settings: Settings,
    items: List[InvestigationQuestionItem],
    *,
    normalized: Optional[Dict[str, Any]] = None,
    search_name: str = "",
    sid: Optional[str] = None,
    splunk_results: Optional[List[dict]] = None,
    refine_on_error: bool = True,
) -> List[InvestigationQuestionItem]:
    """Validate SPL via Splunk parser; optionally refine on parser errors."""
    validated: List[InvestigationQuestionItem] = []
    norm = normalized or {}
    rows = splunk_results or []
    for item in items:
        spl = sanitize_spl_draft(item.spl or "")
        rc = RootCauseSpl(
            spl=spl,
            explanation=item.explanation,
            time_window=item.time_window,
            pivots=item.pivots,
            notes=list(item.notes or []),
            validation=item.validation,
        )
        rc.validation = await validate_root_cause_spl(settings, rc)
        notes = list(item.notes or [])
        if refine_on_error and spl_validation_is_error(rc.validation):
            rc, fixed = await refine_root_cause_spl_until_valid(
                settings,
                rc,
                normalized=norm,
                search_name=search_name or None,
                sid=sid,
                splunk_results=rows,
                objective=item.question,
            )
            if fixed:
                spl = sanitize_spl_draft(rc.spl or spl)
                for n in rc.notes or []:
                    if n not in notes:
                        notes.append(n)
        validated.append(
            item.model_copy(
                update={
                    "spl": spl,
                    "validation": rc.validation,
                    "notes": notes,
                }
            )
        )
    return validated


def investigation_questions_for_verdict(
    verdict: str,
    raw: Any,
    *,
    settings: Optional[Settings] = None,
    max_items: Optional[int] = None,
    legacy_root_spl: Any = None,
    normalized: Optional[Dict[str, Any]] = None,
) -> List[InvestigationQuestionItem]:
    if verdict_implies_false_positive(verdict):
        return []
    limit = max_items
    if limit is None and settings is not None:
        limit = investigation_questions_max(settings)
    if limit is None:
        limit = 3
    return sanitize_investigation_question_items(
        raw,
        legacy_root_spl=legacy_root_spl,
        normalized=normalized,
        max_items=limit,
    )


async def generate_investigation_spl_via_llm(
    settings: Settings,
    *,
    question: str,
    canonical_prefix: str,
    defender_output: Dict[str, Any],
    hunter_output: Dict[str, Any],
    judge_output: Dict[str, Any],
    normalized: Optional[Dict[str, Any]] = None,
    search_name: str = "",
    max_tokens: Optional[int] = None,
) -> Optional[RootCauseSpl]:
    """Generate SPL for one investigation question via analysis LiteLLM."""
    from services.soc_analysis_graph.llm import llm_json_response

    sys_p = load_root_cause_spl_system_prompt()
    from services.llm.llm_context_budget import alert_context_max_chars

    if getattr(settings, "tsoc_spl_compact_context", True):
        user = investigation_question_spl_user_message(
            question=question,
            normalized=normalized or {},
            search_name=search_name,
            alert_max_chars=alert_context_max_chars(settings),
        )
    else:
        user = root_cause_spl_user_message(
            canonical_prefix,
            defender_output,
            hunter_output,
            judge_output,
            investigation_questions=[question],
        )
    mt = max_tokens or min(8192, settings.litellm_analysis_max_tokens)
    try:
        llm_json = await llm_json_response(settings, sys_p, user, max_tokens=mt)
    except Exception as e:
        logger.warning("investigation LLM SPL failed question=%r: %s", question[:80], e)
        return None

    raw_items = llm_json.get("investigation_questions")
    if not isinstance(raw_items, list) or not raw_items:
        return None
    first = raw_items[0]
    if not isinstance(first, dict):
        return None
    rc = sanitize_root_cause_spl_output(first)
    if rc is None or not rc.spl:
        return None
    notes = list(rc.notes or [])
    if "llm_generated_spl" not in notes:
        notes.append("llm_generated_spl")
    rc.notes = notes
    return rc


async def fill_investigation_spl(
    settings: Settings,
    items: List[InvestigationQuestionItem],
    normalized: Optional[Dict[str, Any]],
    *,
    search_name: str = "",
    sid: Optional[str] = None,
    splunk_results: Optional[List[dict]] = None,
    canonical_prefix: str = "",
    defender_output: Optional[Dict[str, Any]] = None,
    hunter_output: Optional[Dict[str, Any]] = None,
    judge_output: Optional[Dict[str, Any]] = None,
) -> tuple[List[InvestigationQuestionItem], str]:
    """
    Per-question SPL: LiteLLM when enabled, else rule-based ``search`` fallback.
    """
    norm = normalized or {}
    rows = splunk_results or []
    d_def = defender_output or {}
    d_hunt = hunter_output or {}
    d_judge = judge_output or {}
    out: List[InvestigationQuestionItem] = []
    used_llm = False
    used_predict = False
    used_saia = False

    from config import mcp_configured
    from services.investigation.spl_saia_analysis import saia_spl_review_requested

    saia_review = saia_spl_review_requested(settings)
    mcp_client = None
    if saia_review and mcp_configured(settings):
        from splunk.mcp.client import SplunkMcpClient

        try:
            mcp_client = SplunkMcpClient(settings)
            await mcp_client.ensure_ready()
        except Exception as e:
            logger.info("fill_investigation_spl SAIA MCP init skipped: %s", e)
            mcp_client = None

    for item in items:
        rc: Optional[RootCauseSpl] = None
        notes = list(item.notes or [])

        if getattr(settings, "tsoc_spl_use_rest_predict", True):
            prompt = build_predict_prompt(
                objective=item.question,
                search_name=search_name,
                normalized=norm,
                splunk_results=rows,
            )
            rc = await generate_spl_via_predict(settings, prompt=prompt)
            if rc is not None and rc.spl:
                used_predict = True
                if "rest_predict_write_spl" not in notes:
                    notes.append("rest_predict_write_spl")

        if rc is None or not rc.spl:
            rc = await generate_investigation_spl_via_llm(
                settings,
                question=item.question,
                canonical_prefix=canonical_prefix,
                defender_output=d_def,
                hunter_output=d_hunt,
                judge_output=d_judge,
                normalized=norm,
                search_name=search_name,
            )
            if rc is not None and rc.spl:
                used_llm = True
                rc.spl = sanitize_spl_draft(rc.spl)
                rc.validation = await validate_root_cause_spl(settings, rc)
                if spl_validation_is_error(rc.validation):
                    rc, parser_fixed = await refine_root_cause_spl_until_valid(
                        settings,
                        rc,
                        normalized=norm,
                        search_name=search_name or None,
                        sid=sid,
                        splunk_results=rows,
                        objective=item.question,
                    )
                    if parser_fixed and "llm_refine_after_parser_error_1" not in notes:
                        notes.append("llm_refine_after_parser_error_1")

        if rc is None or not rc.spl:
            rc = build_rule_based_root_cause_spl(norm)
            if "rule_based_fallback" not in notes:
                notes.append("rule_based_fallback")

        for n in rc.notes or []:
            if n not in notes:
                notes.append(n)

        final_spl = sanitize_spl_draft(rc.spl or "")
        tw = normalize_execution_time_window(rc.time_window or item.time_window)
        filled = item.model_copy(
            update={
                "spl": final_spl,
                "explanation": rc.explanation or item.explanation,
                "time_window": tw,
                "pivots": rc.pivots or item.pivots,
                "notes": notes,
                "validation": rc.validation,
            }
        )
        if saia_review:
            enriched = await enrich_investigation_item_with_saia(
                settings,
                filled,
                search_name=search_name,
                mcp_client=mcp_client,
            )
            if enriched.spl_saia_analysis is not None:
                used_saia = True
            out.append(enriched)
        else:
            out.append(filled)

    if used_predict:
        aggregate = "rest_predict"
    elif used_llm:
        aggregate = "llm"
    else:
        aggregate = "rule_based"
    if used_saia:
        aggregate = "{0}+saia".format(aggregate)
    return out, aggregate


async def run_investigation_item_execute_refine_loop(
    settings: Settings,
    item: InvestigationQuestionItem,
    *,
    normalized: Dict[str, Any],
    search_name: str,
    sid: Optional[str],
    splunk_results: List[dict],
    client: SplunkRestClient,
    session_key: str,
    mcp_client: Any = None,
) -> InvestigationQuestionItem:
    """Execute SPL; on error or 0 rows, refine with LiteLLM (max N attempts)."""
    max_refine = int(getattr(settings, "tsoc_spl_execute_refine_max_attempts", 2) or 0)
    max_refine = max(0, min(2, max_refine))

    validated = await validate_investigation_question_items(
        settings,
        [item],
        normalized=normalized,
        search_name=search_name,
        sid=sid,
        splunk_results=splunk_results,
    )
    current = validated[0] if validated else item
    current = await execute_investigation_item(
        settings,
        current,
        client=client,
        session_key=session_key,
        mcp_client=mcp_client,
    )

    if not needs_spl_execution_refine(current.spl_results):
        return current

    refine_count = 0
    while refine_count < max_refine and needs_spl_execution_refine(current.spl_results):
        refine_count += 1
        logger.info(
            "investigation_spl refine attempt=%d/%d question=%s",
            refine_count,
            max_refine,
            (current.question or "")[:80],
        )
        rc = RootCauseSpl(
            spl=current.spl,
            explanation=current.explanation,
            time_window=current.time_window,
            pivots=list(current.pivots or []),
            notes=list(current.notes or []),
            validation=current.validation,
        )
        rc, llm_ok = await review_spl_after_execution_with_llm(
            settings,
            draft=rc,
            normalized=normalized,
            search_name=search_name or None,
            sid=sid,
            splunk_results=splunk_results,
            objective=current.question,
            execution_result=current.spl_results,
            attempt=refine_count,
        )
        notes = list(current.notes or [])
        refined_rc: Optional[RootCauseSpl] = None
        if llm_ok:
            refined_rc = sanitize_root_cause_spl_output(
                {
                    "spl": rc.spl,
                    "explanation": rc.explanation,
                    "time_window": rc.time_window or current.time_window,
                    "pivots": rc.pivots,
                    "notes": rc.notes,
                }
            )
        if refined_rc is None or not refined_rc.spl:
            fb = build_zero_row_fallback_spl(
                current.question or "",
                normalized,
                prior_spl=current.spl or "",
            )
            if fb is not None and fb.spl:
                refined_rc = fb
                if "auto_fallback_after_zero_rows" not in notes:
                    notes.append("auto_fallback_after_zero_rows")
                logger.info(
                    "investigation_spl auto fallback SPL after refine miss question=%s",
                    (current.question or "")[:80],
                )
        if refined_rc is not None and refined_rc.spl:
            for n in refined_rc.notes or []:
                if n not in notes:
                    notes.append(n)
            current = current.model_copy(
                update={
                    "spl": sanitize_spl_draft(refined_rc.spl),
                    "explanation": refined_rc.explanation or current.explanation,
                    "time_window": normalize_execution_time_window(
                        refined_rc.time_window or current.time_window
                    ),
                    "pivots": refined_rc.pivots or current.pivots,
                    "notes": notes,
                    "validation": refined_rc.validation,
                }
            )

        validated = await validate_investigation_question_items(
            settings,
            [current],
            normalized=normalized,
            search_name=search_name,
            sid=sid,
            splunk_results=splunk_results,
        )
        current = validated[0] if validated else current
        current = await execute_investigation_item(
            settings,
            current,
            client=client,
            session_key=session_key,
            mcp_client=mcp_client,
        )

    notes = list(current.notes or [])
    if refine_count >= max_refine and needs_spl_execution_refine(current.spl_results):
        if "execute_refine_exhausted" not in notes:
            notes.append("execute_refine_exhausted")
        current = current.model_copy(update={"notes": notes})

    result_analysis = await analyze_spl_execution_results_with_llm(
        settings,
        question=current.question or "",
        spl=current.spl or "",
        normalized=normalized,
        search_name=search_name or None,
        sid=sid,
        splunk_results=splunk_results,
        execution_result=current.spl_results,
    )
    if result_analysis:
        notes = list(current.notes or [])
        if "llm_result_batch_analysis" not in notes:
            notes.append("llm_result_batch_analysis")
        current = current.model_copy(
            update={
                "spl_results_analysis": result_analysis,
                "notes": notes,
            }
        )

    return current


async def finalize_investigation_questions_for_verdict(
    settings: Settings,
    verdict: str,
    raw: Any,
    *,
    legacy_root_spl: Any = None,
    normalized: Optional[Dict[str, Any]] = None,
    search_name: str = "",
    sid: Optional[str] = None,
    splunk_results: Optional[List[dict]] = None,
    canonical_prefix: str = "",
    defender_output: Optional[Dict[str, Any]] = None,
    hunter_output: Optional[Dict[str, Any]] = None,
    judge_output: Optional[Dict[str, Any]] = None,
) -> List[InvestigationQuestionItem]:
    items = investigation_questions_for_verdict(
        verdict,
        raw,
        settings=settings,
        legacy_root_spl=legacy_root_spl,
        normalized=normalized,
    )
    if not items:
        return []

    norm = normalized or {}

    items, spl_source = await fill_investigation_spl(
        settings,
        items,
        norm,
        search_name=search_name,
        sid=sid,
        splunk_results=splunk_results,
        canonical_prefix=canonical_prefix,
        defender_output=defender_output,
        hunter_output=hunter_output,
        judge_output=judge_output,
    )
    logger.info(
        "investigation_spl pipeline source=%s question_count=%d",
        spl_source,
        len(items),
    )

    items = await validate_investigation_question_items(
        settings,
        items,
        normalized=normalized,
        search_name=search_name,
        sid=sid,
        splunk_results=splunk_results,
    )

    if not getattr(settings, "tsoc_execute_investigation_spl", True):
        return items
    if not settings.splunk_username or not settings.splunk_password:
        return items

    from config import mcp_configured

    client = SplunkRestClient(settings)
    try:
        session_key = await client.login()
    except Exception as e:
        logger.info("investigation_spl_execute login skipped: %s", e)
        return items

    mcp_client = None
    if mcp_configured(settings) and bool(getattr(settings, "tsoc_spl_execute_via_mcp", True)):
        from splunk.mcp.client import SplunkMcpClient

        try:
            mcp_client = SplunkMcpClient(settings)
            await mcp_client.ensure_ready()
        except Exception as e:
            logger.info("investigation_spl_finalize MCP init skipped: %s", e)
            mcp_client = None

    rows = splunk_results or []
    finalized: List[InvestigationQuestionItem] = []
    for item in items:
        finalized.append(
            await run_investigation_item_execute_refine_loop(
                settings,
                item,
                normalized=norm,
                search_name=search_name,
                sid=sid,
                splunk_results=rows,
                client=client,
                session_key=session_key,
                mcp_client=mcp_client,
            )
        )
    logger.info(
        "investigation_spl execute+refine done questions=%d max_refine=%d",
        len(finalized),
        getattr(settings, "tsoc_spl_execute_refine_max_attempts", 2),
    )
    return finalized
