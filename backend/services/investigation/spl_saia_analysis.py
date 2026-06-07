"""SAIA MCP explain/optimize review for SPL drafted during SOC analysis."""

from __future__ import annotations

import logging
from typing import Any, List, Optional, Tuple

from config import Settings, mcp_configured
from models.analysis import RootCauseSpl, SplSaiaAnalysis
from splunk.mcp.client import SplunkMcpClient
from splunk.mcp.saia.tools import call_saia_explain, call_saia_optimize
from splunk.mcp.tool_registry import McpLogicalTool, resolve_tool_name

logger = logging.getLogger(__name__)


def saia_spl_review_requested(settings: Settings) -> bool:
    """Default on: run SAIA explain/optimize for each investigation SPL in Analysis."""
    return bool(getattr(settings, "tsoc_analysis_saia_spl_review", True))


def _saia_review_enabled(settings: Settings) -> bool:
    if not saia_spl_review_requested(settings):
        return False
    if not mcp_configured(settings):
        return False
    return bool(
        getattr(settings, "tsoc_mcp_saia_optimize_spl", True)
        or getattr(settings, "tsoc_mcp_saia_explain_spl", True)
    )


def _saia_unavailable_reason(settings: Settings) -> str:
    if not mcp_configured(settings):
        return "MCP not configured (enable TSOC_MCP_ENABLED and SPLUNK_MCP_URL/TOKEN)."
    if not (
        getattr(settings, "tsoc_mcp_saia_optimize_spl", True)
        or getattr(settings, "tsoc_mcp_saia_explain_spl", True)
    ):
        return "SAIA SPL review is on but both optimize and explain are disabled in settings."
    return "SAIA tools unavailable."


async def analyze_investigation_spl_with_saia(
    settings: Settings,
    *,
    spl: str,
    explanation: str = "",
    question: str = "",
    search_name: str = "",
    mcp_client: Optional[SplunkMcpClient] = None,
) -> Tuple[str, str, Optional[SplSaiaAnalysis]]:
    """
    Run SAIA ``saia_optimize_spl`` / ``saia_explain_spl`` on an existing SPL.

    Returns (final_spl, final_explanation, analysis or None when skipped/unavailable).
    """
    spl_in = (spl or "").strip()
    if not spl_in:
        return spl_in, explanation, None
    if not saia_spl_review_requested(settings):
        return spl_in, explanation, None
    if not _saia_review_enabled(settings):
        return spl_in, explanation, SplSaiaAnalysis(unavailable_reason=_saia_unavailable_reason(settings))

    client = mcp_client
    owns_client = False
    if client is None:
        try:
            client = SplunkMcpClient(settings)
            owns_client = True
            await client.ensure_ready()
        except Exception as e:
            logger.info("spl_saia_analysis MCP init skipped: %s", e)
            return spl_in, explanation, SplSaiaAnalysis(unavailable_reason=str(e))

    has_optimize = bool(resolve_tool_name(client.tool_names, McpLogicalTool.SAIA_OPTIMIZE_SPL))
    has_explain = bool(resolve_tool_name(client.tool_names, McpLogicalTool.SAIA_EXPLAIN_SPL))
    if not has_optimize and not has_explain:
        return spl_in, explanation, SplSaiaAnalysis(
            unavailable_reason="saia_optimize_spl and saia_explain_spl not listed on MCP server"
        )

    rc = RootCauseSpl(spl=spl_in, explanation=explanation or "")
    steps: List[str] = []
    spl_before: Optional[str] = None
    optimized = False
    context = search_name or question[:120] or None

    try:
        if getattr(settings, "tsoc_mcp_saia_optimize_spl", True) and has_optimize:
            spl_before = rc.spl
            if await call_saia_optimize(client, rc, search_name=context):
                steps.append("optimize")
                optimized = bool(spl_before and rc.spl and rc.spl.strip() != spl_before.strip())

        if getattr(settings, "tsoc_mcp_saia_explain_spl", True) and has_explain:
            if await call_saia_explain(
                client,
                rc,
                search_name=context,
                objective=question or None,
            ):
                steps.append("explain")

        if not steps:
            return spl_in, explanation, SplSaiaAnalysis(
                unavailable_reason="SAIA tools present but optimize/explain returned no output"
            )

        final_spl = (rc.spl or spl_in).strip()
        final_expl = (rc.explanation or explanation or "").strip()
        analysis = SplSaiaAnalysis(
            explanation=final_expl,
            optimized=optimized,
            spl_before_optimize=spl_before if optimized else None,
            steps=steps,
        )
        return final_spl, final_expl, analysis
    except Exception as e:
        logger.warning("spl_saia_analysis failed question=%r: %s", (question or "")[:80], e)
        return spl_in, explanation, SplSaiaAnalysis(unavailable_reason=str(e))
    finally:
        if owns_client and client is not None:
            close = getattr(client, "close", None)
            if callable(close):
                try:
                    result = close()
                    if hasattr(result, "__await__"):
                        await result
                except Exception:
                    pass


async def enrich_investigation_item_with_saia(
    settings: Settings,
    item: Any,
    *,
    search_name: str = "",
    mcp_client: Optional[SplunkMcpClient] = None,
) -> Any:
    """Attach ``spl_saia_analysis`` and merge SAIA explanation into the question item."""
    from models.analysis import InvestigationQuestionItem

    if not isinstance(item, InvestigationQuestionItem):
        return item
    if not (item.spl or "").strip():
        return item
    if not saia_spl_review_requested(settings):
        return item

    final_spl, final_expl, analysis = await analyze_investigation_spl_with_saia(
        settings,
        spl=item.spl,
        explanation=item.explanation or "",
        question=item.question or "",
        search_name=search_name,
        mcp_client=mcp_client,
    )
    if analysis is None:
        return item

    notes = list(item.notes or [])
    if "optimize" in analysis.steps and "mcp_saia_optimize_spl" not in notes:
        notes.append("mcp_saia_optimize_spl")
    if "explain" in analysis.steps and "mcp_saia_explain_spl" not in notes:
        notes.append("mcp_saia_explain_spl")
    if "mcp_saia_analysis" not in notes:
        notes.append("mcp_saia_analysis")

    return item.model_copy(
        update={
            "spl": final_spl,
            "explanation": final_expl or item.explanation,
            "spl_saia_analysis": analysis,
            "notes": notes,
        }
    )
