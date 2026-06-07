"""Build MCP ``saia_generate_spl`` request arguments."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from config import Settings

from .constants import SAIA_SPL_INSTRUCTION


def truncate_saia_prompt(text: str, max_chars: int) -> str:
    s = (text or "").strip()
    if len(s) <= max_chars:
        return s
    if max_chars <= 1:
        return s[:max_chars]
    return s[: max_chars - 1] + "…"


def build_saia_generate_args(
    settings: Settings,
    *,
    normalized: Dict[str, Any],
    search_name: Optional[str],
    objective: Optional[str],
    cim_schema_summary: str = "",
    datamodel: Optional[str] = None,
    index: Optional[str] = None,
    context: Optional[str] = None,
    saia_prompt: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build MCP ``saia_generate_spl`` arguments.

    MCP limits ``prompt`` to 1000 characters; alert JSON and CIM schema go in ``additional_context``.
    """
    from services.llm.llm_context_budget import saia_aux_context_max_chars, saia_mcp_prompt_max_chars

    max_prompt = saia_mcp_prompt_max_chars(settings)
    if (saia_prompt or "").strip():
        prompt = truncate_saia_prompt(saia_prompt.strip(), max_prompt)
    else:
        obj = (objective or "").strip()
        alert_label = (search_name or "alert").strip()[:120]
        prompt_parts: List[str] = []
        prompt_parts.append("Alert: {0}.".format(alert_label))
        if obj:
            prompt_parts.append("Question: {0}.".format(obj))
        if datamodel:
            prompt_parts.append("Prefer CIM datamodel={0}.".format(datamodel))
        prompt_parts.append(SAIA_SPL_INSTRUCTION)
        prompt = " ".join(prompt_parts)
        if len(prompt) > max_prompt:
            fixed = "Alert: {0}. {1}".format(alert_label, SAIA_SPL_INSTRUCTION)
            if datamodel:
                fixed += " Prefer CIM datamodel={0}.".format(datamodel)
            room = max_prompt - len(fixed) - len("Question: . ")
            if room > 40 and obj:
                q = truncate_saia_prompt(obj, room)
                prompt = "Alert: {0}. Question: {1}. {2}".format(
                    alert_label,
                    q,
                    SAIA_SPL_INSTRUCTION + (
                        " Prefer CIM datamodel={0}.".format(datamodel) if datamodel else ""
                    ),
                )
            else:
                prompt = truncate_saia_prompt(prompt, max_prompt)

    ctx_parts: List[str] = []
    if index:
        ctx_parts.append("index={0}".format(index))
    if context and context != search_name:
        ctx_parts.append("context={0}".format(context))
    if cim_schema_summary:
        ctx_parts.append("CIM schema (datamodelsimple):\n{0}".format(cim_schema_summary))
    if normalized:
        ctx_parts.append(
            "Alert fields JSON: {0}".format(
                json.dumps(normalized, ensure_ascii=False, default=str)
            )
        )

    args: Dict[str, Any] = {
        "prompt": prompt,
        "spl_only": bool(getattr(settings, "tsoc_mcp_saia_spl_only", False)),
    }
    if ctx_parts:
        cap = saia_aux_context_max_chars(settings)
        args["additional_context"] = "\n\n".join(ctx_parts)[:cap]
    return args


def build_nl_query(
    settings: Settings,
    *,
    normalized: Dict[str, Any],
    search_name: Optional[str],
    objective: Optional[str],
    cim_schema_summary: str = "",
    datamodel: Optional[str] = None,
    index: Optional[str] = None,
    context: Optional[str] = None,
) -> str:
    """Compact prompt for trace logs (same as MCP ``prompt`` field)."""
    return build_saia_generate_args(
        settings,
        normalized=normalized,
        search_name=search_name,
        objective=objective,
        cim_schema_summary=cim_schema_summary,
        datamodel=datamodel,
        index=index,
        context=context,
    ).get("prompt", "")
