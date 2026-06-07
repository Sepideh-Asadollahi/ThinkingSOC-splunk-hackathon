"""LLM helpers for Observability pipeline stages."""

from __future__ import annotations

import json
from typing import Any, Dict, List

from config import Settings
from models.observability import DiagnoserSection, OpsJudgeVerdict, ResponderSection, RootCauseHypothesis
from services.llm.litellm_service import litellm_chat_completion
from services.observability_analysis.observability_prompts import (
    load_observability_diagnoser_system_prompt,
    load_observability_ops_judge_system_prompt,
    load_observability_responder_system_prompt,
)
from services.soc_analysis.soc_analysis_json import parse_llm_json_response


def _context_json(ctx: Dict[str, Any]) -> str:
    return json.dumps(ctx, ensure_ascii=False, indent=2)


async def _llm_json_response(settings: Settings, system_prompt: str, user_message: str) -> Dict[str, Any]:
    out = await litellm_chat_completion(
        settings,
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=settings.litellm_analysis_temperature,
        max_tokens=max(512, settings.litellm_analysis_max_tokens // 3),
    )
    return parse_llm_json_response(str(out.get("content") or ""))


def _to_diagnoser(data: Dict[str, Any]) -> DiagnoserSection:
    raw_h = data.get("root_cause_hypotheses")
    hyps: List[RootCauseHypothesis] = []
    if isinstance(raw_h, list):
        for item in raw_h:
            if not isinstance(item, dict):
                continue
            try:
                hyps.append(RootCauseHypothesis(**item))
            except Exception:
                continue
    followup = data.get("followup_searches")
    searches = [str(s) for s in (followup or []) if str(s).strip()] if isinstance(followup, list) else []
    if not hyps:
        hyps = [
            RootCauseHypothesis(
                hypothesis="Insufficient evidence for a strong operational root-cause claim.",
                confidence="low",
                evidence_refs=[],
                what_would_confirm="Collect host/service metrics and logs in the alert window.",
            )
        ]
    return DiagnoserSection(root_cause_hypotheses=hyps, followup_searches=searches)


def _to_responder(data: Dict[str, Any]) -> ResponderSection:
    actions_raw = data.get("recommended_actions")
    notes_raw = data.get("safety_notes")
    actions = [str(a) for a in (actions_raw or []) if str(a).strip()] if isinstance(actions_raw, list) else []
    notes = [str(a) for a in (notes_raw or []) if str(a).strip()] if isinstance(notes_raw, list) else []
    if not actions:
        actions = ["Validate key metrics and logs before disruptive remediation."]
    if not notes:
        notes = ["Prefer reversible actions first and confirm impact scope."]
    return ResponderSection(recommended_actions=actions, safety_notes=notes)


def _to_ops_judge(data: Dict[str, Any]) -> OpsJudgeVerdict:
    clean = {
        "verdict": str(data.get("verdict") or "needs_more_evidence"),
        "priority": str(data.get("priority") or "medium"),
        "recommended_next_step": str(data.get("recommended_next_step") or "Gather more correlated evidence."),
        "confidence": str(data.get("confidence") or "low"),
        "rationale": str(data.get("rationale") or "Judgment is limited by available evidence."),
        "escalation_target": str(data.get("escalation_target") or "service owner"),
    }
    return OpsJudgeVerdict(**clean)


async def build_diagnoser_llm(settings: Settings, context: Dict[str, Any]) -> DiagnoserSection:
    prompt = load_observability_diagnoser_system_prompt()
    user_message = "## System Context\n{0}".format(_context_json(context))
    data = await _llm_json_response(settings, prompt, user_message)
    return _to_diagnoser(data)


async def build_responder_llm(settings: Settings, context: Dict[str, Any]) -> ResponderSection:
    prompt = load_observability_responder_system_prompt()
    user_message = "## System Context\n{0}".format(_context_json(context))
    data = await _llm_json_response(settings, prompt, user_message)
    return _to_responder(data)


async def build_ops_judge_llm(settings: Settings, context: Dict[str, Any]) -> OpsJudgeVerdict:
    prompt = load_observability_ops_judge_system_prompt()
    user_message = "## System Context\n{0}".format(_context_json(context))
    data = await _llm_json_response(settings, prompt, user_message)
    return _to_ops_judge(data)
