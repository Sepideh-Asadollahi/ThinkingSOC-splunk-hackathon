"""Graph nodes: Defender, Hunter, Judge, framework mapping, investigation questions."""

from __future__ import annotations

import json
import logging
from typing import Any, Callable, Dict, List

from config import Settings, investigation_questions_max
from models.mcp import McpHunterEvidence, McpJudgeEvidence
from services.soc_analysis.soc_analysis_prompts import (
    load_defender_system_prompt,
    load_framework_mapping_system_prompt,
    load_hunter_system_prompt,
    load_investigation_questions_system_prompt,
    load_judge_system_prompt,
)
from services.investigation.investigation_question_context import (
    format_alert_fields_block,
    merge_alert_field_sample,
    postprocess_investigation_question_strings,
    primary_alert_fields,
)
from services.soc_analysis.soc_verdict import verdict_implies_false_positive

from services.soc_analysis.fallback_questions import fallback_investigation_questions

from .llm import (
    investigation_questions_max_tokens,
    llm_json_response,
    per_stage_max_tokens,
)
from .messages import (
    defender_user_message,
    framework_mapping_user_message,
    hunter_user_message,
    investigation_questions_user_message,
    judge_user_message,
)
from .state import SocAnalysisGraphState
from .step_logging import run_graph_step
from splunk.mcp.hunter_judge_context import build_hunter_mcp_context, build_judge_mcp_context

logger = logging.getLogger(__name__)


def make_defender_node(settings: Settings, mt: int) -> Callable[..., Any]:
    async def node_defender(state: SocAnalysisGraphState) -> Dict[str, Any]:
        async def work() -> Dict[str, Any]:
            sys_p = load_defender_system_prompt()
            user = defender_user_message(state["canonical_prefix"])
            data = await llm_json_response(settings, sys_p, user, max_tokens=mt)
            return {"defender_output": data}

        return await run_graph_step("defender", state, work)

    return node_defender


def make_hunter_node(settings: Settings, mt: int) -> Callable[..., Any]:
    async def node_hunter(state: SocAnalysisGraphState) -> Dict[str, Any]:
        async def work() -> Dict[str, Any]:
            hunter_mcp = await build_hunter_mcp_context(
                settings,
                normalized=state.get("normalized") or {},
                search_name=state.get("search_name"),
                splunk_results=list(state.get("splunk_results_preview") or []),
                defender_output=state.get("defender_output") or {},
            )
            sys_p = load_hunter_system_prompt()
            user = hunter_user_message(
                state["canonical_prefix"],
                state.get("defender_output") or {},
                hunter_mcp=hunter_mcp,
            )
            data = await llm_json_response(
                settings, sys_p, user, max_tokens=mt, salvage_hunter=True
            )
            out: Dict[str, Any] = {"hunter_output": data}
            if hunter_mcp is not None:
                out["hunter_mcp_context"] = hunter_mcp.model_dump(mode="json")
                logger.info(
                    "soc_graph step=hunter detail sid=%s mcp_tools=%d hunt_queries=%d",
                    state.get("sid"),
                    len(hunter_mcp.tools_called),
                    len(hunter_mcp.hunt_queries),
                )
            return out

        return await run_graph_step("hunter", state, work)

    return node_hunter


def make_judge_node(settings: Settings, mt: int) -> Callable[..., Any]:
    async def node_judge(state: SocAnalysisGraphState) -> Dict[str, Any]:
        async def work() -> Dict[str, Any]:
            hunter_mcp_raw = state.get("hunter_mcp_context")
            hunter_mcp = (
                McpHunterEvidence.model_validate(hunter_mcp_raw)
                if isinstance(hunter_mcp_raw, dict) and hunter_mcp_raw
                else None
            )
            judge_mcp = await build_judge_mcp_context(
                settings,
                normalized=state.get("normalized") or {},
                search_name=state.get("search_name"),
                defender_output=state.get("defender_output") or {},
                hunter_output=state.get("hunter_output") or {},
                hunter_mcp=hunter_mcp,
            )
            sys_p = load_judge_system_prompt()
            user = judge_user_message(
                state["canonical_prefix"],
                state.get("defender_output") or {},
                state.get("hunter_output") or {},
                hunter_mcp=hunter_mcp,
                judge_mcp=judge_mcp,
            )
            data = await llm_json_response(
                settings,
                sys_p,
                user,
                max_tokens=min(mt * 2, settings.litellm_analysis_max_tokens),
            )
            jn = data.get("judge")
            verdict = str(jn.get("verdict") or "") if isinstance(jn, dict) else ""
            logger.info(
                "soc_graph step=judge detail sid=%s verdict=%s mcp_saia=%d mcp_verify=%d",
                state.get("sid"),
                verdict[:160] if verdict else "",
                len(judge_mcp.saia_answers) if judge_mcp else 0,
                len(judge_mcp.verification_queries) if judge_mcp else 0,
            )
            out: Dict[str, Any] = {"judge_output": data}
            if judge_mcp is not None:
                out["judge_mcp_context"] = judge_mcp.model_dump(mode="json")
            return out

        return await run_graph_step("judge", state, work)

    return node_judge


def make_framework_mapping_node(settings: Settings, mt: int) -> Callable[..., Any]:
    async def node_framework_mapping(state: SocAnalysisGraphState) -> Dict[str, Any]:
        async def work() -> Dict[str, Any]:
            sys_p = load_framework_mapping_system_prompt()
            judge_output = state.get("judge_output") or {}
            user = framework_mapping_user_message(
                state["canonical_prefix"],
                state.get("defender_output") or {},
                state.get("hunter_output") or {},
                judge_output,
            )
            data = await llm_json_response(settings, sys_p, user, max_tokens=mt)
            return {"framework_mapping_output": data}

        return await run_graph_step("framework_mapping", state, work)

    return node_framework_mapping


def make_investigation_questions_node(settings: Settings, mt: int) -> Callable[..., Any]:
    async def node_investigation_questions(state: SocAnalysisGraphState) -> Dict[str, Any]:
        async def work() -> Dict[str, Any]:
            judge_output = state.get("judge_output") or {}
            verdict = str((judge_output.get("judge") or {}).get("verdict") or "")
            if verdict_implies_false_positive(verdict):
                logger.info(
                    "soc_graph step=investigation_questions detail sid=%s mode=skipped_false_positive verdict=%s",
                    state.get("sid"),
                    verdict[:120] if verdict else "",
                )
                return {"investigation_questions_output": {"investigation_questions": []}}

            max_q = investigation_questions_max(settings)
            sample = merge_alert_field_sample(
                state.get("normalized") or {},
                state.get("splunk_results_preview"),
            )
            sn = str(state.get("search_name") or "").strip()
            fields = primary_alert_fields(sample, search_name=sn)
            fields_block = format_alert_fields_block(fields, search_name=sn)
            sys_p = load_investigation_questions_system_prompt()
            user = investigation_questions_user_message(
                state["canonical_prefix"],
                state.get("defender_output") or {},
                state.get("hunter_output") or {},
                judge_output,
                max_questions=max_q,
                alert_fields_block=fields_block,
            )
            iq_mt = investigation_questions_max_tokens(settings, mt)
            mode = "llm"
            try:
                data = await llm_json_response(
                    settings,
                    sys_p,
                    user,
                    max_tokens=iq_mt,
                    salvage_investigation=True,
                )
            except json.JSONDecodeError:
                data = {}
                mode = "fallback_parse_error"

            def _postprocess(raw_list: Any) -> List[str]:
                return postprocess_investigation_question_strings(
                    raw_list,
                    normalized=state.get("normalized"),
                    splunk_results=state.get("splunk_results_preview"),
                    search_name=sn,
                    max_items=max_q,
                )

            raw_iq = data.get("investigation_questions")
            if isinstance(raw_iq, list):
                data["investigation_questions"] = _postprocess(raw_iq)
            elif isinstance(data.get("questions"), list):
                data["investigation_questions"] = _postprocess(data.get("questions"))
                data.pop("questions", None)

            processed = data.get("investigation_questions") or []
            min_expected = min(max_q, 2)
            if len(processed) < min_expected:
                fb = fallback_investigation_questions(
                    state.get("normalized") or {},
                    state.get("splunk_results_preview") or [],
                    max_items=max_q,
                )
                merged: List[str] = list(processed)
                for q in fb:
                    if q not in merged:
                        merged.append(q)
                    if len(merged) >= max_q:
                        break
                if len(merged) > len(processed):
                    mode = "fallback_supplement" if processed else "fallback_rule_based"
                data["investigation_questions"] = merged[:max_q]
                notes = data.get("notes")
                if not isinstance(notes, list):
                    notes = []
                notes.append(mode)
                data["notes"] = notes

            raw_iq = data.get("investigation_questions")
            raw_q = data.get("questions")
            if isinstance(raw_iq, list):
                nq = len(raw_iq)
            elif isinstance(raw_q, list):
                nq = len(raw_q)
            else:
                nq = 0
            logger.info(
                "soc_graph step=investigation_questions detail sid=%s mode=%s question_count=%d max_tokens=%d",
                state.get("sid"),
                mode,
                nq,
                iq_mt,
            )
            return {"investigation_questions_output": data}

        return await run_graph_step("investigation_questions", state, work)

    return node_investigation_questions


def make_llm_nodes_bundle(settings: Settings):
    """Return ``mt`` and all LLM-stage node callables (shared per-stage token budget)."""
    mt = per_stage_max_tokens(settings)
    return {
        "mt": mt,
        "defender": make_defender_node(settings, mt),
        "hunter": make_hunter_node(settings, mt),
        "judge": make_judge_node(settings, mt),
        "framework_mapping": make_framework_mapping_node(settings, mt),
        "investigation_questions": make_investigation_questions_node(settings, mt),
    }
