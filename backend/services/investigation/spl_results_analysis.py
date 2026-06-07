"""LLM analysis for executed investigation SPL result batches."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from config import Settings
from models.analysis import SplSearchResult
from services.soc_analysis.soc_analysis_canonical import build_canonical_static_context
from services.soc_analysis_graph.llm import llm_json_response, spl_review_max_tokens
from services.soc_analysis.soc_analysis_prompts import load_prompt_file

logger = logging.getLogger(__name__)

_PROMPT_SPL_RESULTS_ANALYSIS = "prompt_spl_results_analysis_system.md"


def _batched_execution_rows(
    settings: Settings, result: Optional[SplSearchResult]
) -> Dict[str, Any]:
    from services.llm.llm_context_budget import context_input_char_budget

    if result is None:
        return {"row_count": 0, "included_row_count": 0, "rows": []}

    rows = list(result.rows or [])
    max_chars = max(4096, int(context_input_char_budget(settings) * 0.35))
    used = 0
    included: List[Dict[str, Any]] = []
    for row in rows:
        blob = json.dumps(row, ensure_ascii=False, default=str)
        if included and (used + len(blob)) > max_chars:
            break
        included.append(row)
        used += len(blob)

    return {
        "row_count": int(result.row_count or 0),
        "included_row_count": len(included),
        "omitted_row_count": max(0, len(rows) - len(included)),
        "truncated": bool(result.truncated),
        "error": result.error,
        "rows": included,
    }


def _spl_results_analysis_user_message(
    *,
    canonical: str,
    question: str,
    spl: str,
    result_batch: Dict[str, Any],
) -> str:
    return (
        "Analyze the SPL execution outcome as one batched dataset (not row-by-row).\n\n"
        "## System Context\n"
        + canonical
        + "\n\n## Investigation question\n"
        + (question or "(none)")
        + "\n\n## Executed SPL\n"
        + (spl or "")
        + "\n\n## Batched SPL execution result\n"
        + json.dumps(result_batch, ensure_ascii=False, default=str)
    )


async def analyze_spl_execution_results_with_llm(
    settings: Settings,
    *,
    question: str,
    spl: str,
    normalized: Dict[str, Any],
    search_name: Optional[str],
    sid: Optional[str],
    splunk_results: List[Dict[str, Any]],
    execution_result: Optional[SplSearchResult],
    enrichment: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Analyze each SPL execution result as a separate batch."""
    identity = enrichment or {
        "resolved_asset_id": None,
        "resolved_user_id": None,
        "matched_relationship_ids": [],
        "confidence": "low",
        "notes": "not provided for SPL result analysis",
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
    sys_p = load_prompt_file(_PROMPT_SPL_RESULTS_ANALYSIS)
    result_batch = _batched_execution_rows(settings, execution_result)
    user = _spl_results_analysis_user_message(
        canonical=canonical,
        question=question,
        spl=spl,
        result_batch=result_batch,
    )
    try:
        llm_json = await llm_json_response(
            settings,
            sys_p,
            user,
            max_tokens=spl_review_max_tokens(settings),
        )
    except Exception as e:
        logger.warning("spl results analysis failed question=%r: %s", question[:80], e)
        return None

    if not isinstance(llm_json, dict):
        return None
    analysis = llm_json.get("result_analysis")
    if isinstance(analysis, dict):
        return analysis
    return llm_json
