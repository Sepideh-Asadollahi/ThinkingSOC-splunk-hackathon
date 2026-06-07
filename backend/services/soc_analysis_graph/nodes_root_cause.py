"""Graph node: pass investigation questions to assembly (SPL via MCP SAIA in finalize)."""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict

from config import Settings, investigation_questions_max, mcp_configured
from services.investigation.investigation_questions_spl import investigation_questions_for_verdict
from services.soc_analysis.soc_verdict import sanitize_investigation_questions

from .state import SocAnalysisGraphState
from .step_logging import run_graph_step

logger = logging.getLogger(__name__)


def make_root_cause_spl_node(settings: Settings, mt: int) -> Callable[..., Any]:
    async def node_root_cause_spl(state: SocAnalysisGraphState) -> Dict[str, Any]:
        async def work() -> Dict[str, Any]:
            normalized = state.get("normalized") or {}
            judge_output = state.get("judge_output") or {}
            verdict = str((judge_output.get("judge") or {}).get("verdict") or "")

            inv_out = state.get("investigation_questions_output") or {}
            max_q = investigation_questions_max(settings)
            question_strings = sanitize_investigation_questions(
                inv_out.get("investigation_questions"), max_items=max_q
            )

            if not question_strings:
                items = investigation_questions_for_verdict(
                    verdict, [], settings=settings, normalized=normalized
                )
                return {
                    "investigation_questions_output": {
                        "investigation_questions": [x.model_dump(mode="json") for x in items],
                    },
                }

            # SPL generation (MCP SAIA) runs once in assembly.finalize_investigation_questions_for_verdict.
            payload = [{"question": q} for q in question_strings]
            logger.info(
                "soc_graph step=root_cause_spl detail sid=%s question_count=%d mcp_pending=%s",
                state.get("sid"),
                len(payload),
                mcp_configured(settings),
            )
            return {"investigation_questions_output": {"investigation_questions": payload}}

        return await run_graph_step("root_cause_spl", state, work)

    return node_root_cause_spl
