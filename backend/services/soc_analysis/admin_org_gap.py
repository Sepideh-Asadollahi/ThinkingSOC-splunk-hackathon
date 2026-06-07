"""Suggest a single organizational GAP question for an admin (simplified vs ThinkingSOC)."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from config import Settings
from models.admin_org import AdminOrgGapSuggestRequest, AdminOrgGapSuggestResponse
from models.analysis import AnalysisRunRequest, SocAnalysisResult
from services.llm.litellm_service import LiteLLMNotConfiguredError, litellm_chat_completion
from services.splunk_json_store import persist_admin_org_gap_to_splunk
from services.soc_analysis.soc_analysis_json import parse_llm_json_response
from services.soc_analysis.soc_analysis_prompts import load_admin_org_gap_system_prompt

logger = logging.getLogger(__name__)

_EXCERPT_MAX = 2000

# Process / behavior hints that warrant an org-policy question even when inventory links the host.
_PROCESS_GAP_PATTERNS: Tuple[Tuple[re.Pattern[str], str, str], ...] = (
    (
        re.compile(r"osk\.exe", re.I),
        "osk.exe (On-Screen Keyboard)",
        "LOLBAS / assistive-tech abuse when launched from scripts or PowerShell",
    ),
    (
        re.compile(r"certutil\.exe", re.I),
        "certutil.exe",
        "LOLBAS file transfer or decode abuse",
    ),
    (
        re.compile(r"regsvr32\.exe", re.I),
        "regsvr32.exe",
        "script proxy / LOLBAS execution",
    ),
    (
        re.compile(r"mshta\.exe", re.I),
        "mshta.exe",
        "HTA / script execution policy",
    ),
    (
        re.compile(r"rundll32\.exe", re.I),
        "rundll32.exe",
        "unusual DLL execution or LOLBAS",
    ),
)

_LOLBAS_TEXT_HINTS = ("lolbas", "living off the land", "t1218", "assistive-tech")


def _truncate(text: Optional[str], limit: int = _EXCERPT_MAX) -> Optional[str]:
    if not text:
        return None
    s = str(text).strip()
    if not s:
        return None
    return s[:limit] if len(s) > limit else s


def _alert_text_blob(normalized: Dict[str, Any]) -> str:
    parts: List[str] = []
    for key in (
        "Image",
        "image",
        "ParentImage",
        "parentimage",
        "CommandLine",
        "commandline",
        "ParentCommandLine",
        "signature",
        "signature_id",
        "search_name",
    ):
        val = normalized.get(key)
        if val is not None and str(val).strip():
            parts.append(str(val))
    return " ".join(parts).lower()


def _host_label(normalized: Dict[str, Any], inventory_asset: Optional[Dict[str, Any]]) -> str:
    if inventory_asset:
        hn = inventory_asset.get("hostname")
        if hn:
            return str(hn)
    for key in ("host", "Computer", "computer", "dest"):
        val = normalized.get(key)
        if val is not None and str(val).strip():
            return str(val).strip()
    return "this host"


def _detect_process_org_gap(
    normalized: Dict[str, Any],
    *,
    inventory_asset: Optional[Dict[str, Any]] = None,
) -> Optional[Tuple[str, str]]:
    """Return (process_label, risk_note) when org policy on this process is likely unknown."""
    blob = _alert_text_blob(normalized)
    if not blob:
        return None
    for pattern, label, risk_note in _PROCESS_GAP_PATTERNS:
        if pattern.search(blob):
            return label, risk_note
    if any(h in blob for h in _LOLBAS_TEXT_HINTS) and (
        "powershell" in blob or ".exe" in blob or "invoke" in blob
    ):
        return "suspicious process execution", "LOLBAS-style or script-launched binary"
    return None


def _weak_identity(enrichment: Optional[Dict[str, Any]]) -> bool:
    return not (enrichment and enrichment.get("resolved_asset_id"))


def rule_based_admin_org_gap(body: AdminOrgGapSuggestRequest) -> Optional[AdminOrgGapSuggestResponse]:
    """
    Deterministic gaps: ownership when inventory is weak; process/policy when behavior is ambiguous
    even if the host is linked (e.g. botsv1 osk.exe on a known workstation).
    """
    sid = body.sid or "unknown_sid"
    sn = body.search_name or "unknown_search"
    host = _host_label(body.normalized, body.inventory_asset)

    process_gap = _detect_process_org_gap(
        body.normalized,
        inventory_asset=body.inventory_asset,
    )
    if process_gap:
        proc_label, risk_note = process_gap
        return AdminOrgGapSuggestResponse(
            should_suggest_question=True,
            gap_summary=(
                "Inventory may identify the host, but organizational policy is unclear for "
                "{0} in this context ({1}).".format(proc_label, risk_note)
            ),
            question_for_admin=(
                "On workstation '{0}', is {1} an approved process for end users (including when "
                "launched from PowerShell or scripts), or should SOC treat this as unauthorized "
                "activity and escalate to the service owner?".format(host, proc_label)
            ),
            notes="Rule-based process/policy gap. sid={0} search={1}.".format(sid, sn),
        )

    if _weak_identity(body.enrichment):
        return AdminOrgGapSuggestResponse(
            should_suggest_question=True,
            gap_summary=(
                "Asset/user ownership and escalation ownership for this alert context are not fully "
                "established in inventory."
            ),
            question_for_admin=(
                "For alerts from saved search '{0}' involving hosts like those in this ticket, who is the "
                "service owner and which escalation path should SOC use (include after-hours)?".format(sn)
            ),
            notes="Rule-based ownership gap (no LLM). sid={0}.".format(sid),
        )

    return None


def build_admin_org_gap_request(
    body: AnalysisRunRequest,
    result: SocAnalysisResult,
) -> AdminOrgGapSuggestRequest:
    """Build gap-suggest input from a completed SOC analysis."""
    return AdminOrgGapSuggestRequest(
        normalized=body.normalized,
        sid=body.sid,
        search_name=body.search_name,
        enrichment=result.enrichment.model_dump(mode="json"),
        risk_context=result.risk_context,
        defender_text=_truncate(result.defender),
        hunter_text=_truncate(result.hunter.narrative if result.hunter else None),
        judge_verdict=result.judge.verdict,
        judge_rationale=_truncate(result.judge.rationale),
        inventory_user=result.inventory_user,
        inventory_asset=result.inventory_asset,
    )


async def attach_admin_org_gap(
    settings: Settings,
    body: AnalysisRunRequest,
    result: SocAnalysisResult,
) -> SocAnalysisResult:
    """Run admin-org gap suggestion and attach to the SOC result (also persists audit row)."""
    gap_req = build_admin_org_gap_request(body, result)
    gap = await suggest_admin_org_gap(settings, gap_req)
    await persist_admin_org_gap_to_splunk(settings, gap_req, gap)
    return result.model_copy(update={"admin_org_gap": gap})


def _fallback_response(body: AdminOrgGapSuggestRequest) -> AdminOrgGapSuggestResponse:
    """Deterministic hint when LLM is off or unavailable."""
    ruled = rule_based_admin_org_gap(body)
    if ruled:
        return ruled
    sid = body.sid or "unknown_sid"
    return AdminOrgGapSuggestResponse(
        should_suggest_question=False,
        gap_summary="",
        question_for_admin="",
        notes="Rule-based fallback (no LLM): no organizational gap detected. sid={0}.".format(sid),
    )


async def suggest_admin_org_gap(
    settings: Settings,
    body: AdminOrgGapSuggestRequest,
) -> AdminOrgGapSuggestResponse:
    """
    Call LiteLLM with the admin-org gap system prompt; parse JSON.

    If LiteLLM is not configured or fails, return rule-based fallback.
    Rule-based process/ownership gaps also apply when the LLM returns no question.
    """
    ruled = rule_based_admin_org_gap(body)

    payload: Dict[str, Any] = {
        "alert_context": {
            "normalized": body.normalized,
            "sid": body.sid,
            "search_name": body.search_name,
        },
        "enrichment": body.enrichment,
        "inventory_user": body.inventory_user,
        "inventory_asset": body.inventory_asset,
        "risk_context": body.risk_context,
        "analysis_excerpts": {
            "defender": body.defender_text,
            "hunter": body.hunter_text,
            "judge_verdict": body.judge_verdict,
            "judge_rationale": body.judge_rationale,
        },
    }
    user_text = (
        "Identify organizational knowledge gaps and produce the JSON object.\n\n"
        + json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    )

    try:
        out = await litellm_chat_completion(
            settings,
            [
                {"role": "system", "content": load_admin_org_gap_system_prompt()},
                {"role": "user", "content": user_text},
            ],
            temperature=settings.litellm_analysis_temperature,
            max_tokens=max(512, settings.litellm_analysis_max_tokens // 4),
        )
    except (LiteLLMNotConfiguredError, Exception) as e:
        logger.warning("admin_org_gap LLM failed, using fallback: %s", e)
        return _fallback_response(body)

    text = str(out.get("content") or "")
    try:
        data = parse_llm_json_response(text)
    except Exception as e:
        logger.warning("admin_org_gap JSON parse failed: %s", e)
        return _fallback_response(body)

    should = bool(data.get("should_suggest_question"))
    gs = str(data.get("gap_summary") or "").strip()
    q = str(data.get("question_for_admin") or "").strip()
    notes = data.get("notes")
    notes_out = str(notes).strip() if notes is not None else None

    if not should:
        if ruled:
            return ruled
        return AdminOrgGapSuggestResponse(
            should_suggest_question=False,
            gap_summary="",
            question_for_admin="",
            notes=notes_out or None,
        )
    if len(q) < 12:
        return _fallback_response(body)
    return AdminOrgGapSuggestResponse(
        should_suggest_question=True,
        gap_summary=gs[:4000] or "Organizational context gap noted.",
        question_for_admin=q[:4000],
        notes=notes_out,
    )
