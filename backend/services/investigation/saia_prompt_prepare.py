"""LiteLLM step: craft SAIA ``saia_generate_spl`` prompt (≤1000 chars) before MCP call."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional, Tuple

from config import Settings
from services.llm.llm_context_budget import saia_mcp_prompt_max_chars
from services.soc_analysis_graph.llm import llm_json_response
from services.soc_analysis.soc_analysis_prompts import load_prompt_file

logger = logging.getLogger(__name__)

_PROMPT_PREPARE = "prompt_saia_prepare_system.md"
_SAIA_SPL_INSTRUCTION = (
    "Write simple SPL (search/stats/tstats). "
    "No join/append/transaction/map/multisearch/union. "
    "Backend converts to CIM tstats later."
)


def _truncate_saia_prompt(text: str, max_chars: int) -> str:
    s = (text or "").strip()
    if len(s) <= max_chars:
        return s
    if max_chars <= 1:
        return s[:max_chars]
    return s[: max_chars - 1] + "…"


def _compact_alert_for_prepare(normalized: Dict[str, Any]) -> str:
    keys = (
        "host",
        "Computer",
        "user",
        "User",
        "src",
        "dest",
        "Image",
        "ParentImage",
        "ParentCommandLine",
        "CommandLine",
        "index",
        "signature",
        "severity",
    )
    parts = []
    for k in keys:
        if k in normalized and normalized[k] is not None:
            v = normalized[k]
            if isinstance(v, list):
                v = ",".join(str(x) for x in v[:4])
            parts.append("{0}={1}".format(k, str(v)[:160]))
    if len(parts) < 6:
        for k, v in normalized.items():
            if k in keys or str(k).startswith("_"):
                continue
            if v is None:
                continue
            parts.append("{0}={1}".format(k, str(v)[:100]))
            if len(parts) >= 10:
                break
    return "; ".join(parts)


def _prepare_user_message(
    *,
    search_name: Optional[str],
    objective: Optional[str],
    normalized: Dict[str, Any],
    datamodel: Optional[str],
    cim_schema_summary: str,
) -> str:
    schema_block = ""
    if cim_schema_summary:
        schema_block = "\n## CIM schema (summary)\n" + cim_schema_summary[:2000]
    return (
        "Write the saia_prompt JSON for Splunk AI Assistant.\n\n"
        "## Alert\n"
        + (search_name or "(unnamed)")
        + "\n\n## Investigation question\n"
        + (objective or "").strip()
        + "\n\n## Alert field summary\n"
        + _compact_alert_for_prepare(normalized)
        + "\n\n## Suggested CIM datamodel\n"
        + (datamodel or "(infer from question)")
        + schema_block
        + "\n\n## Required SPL style\n"
        + _SAIA_SPL_INSTRUCTION
    )


async def prepare_saia_prompt_with_llm(
    settings: Settings,
    *,
    normalized: Dict[str, Any],
    search_name: Optional[str],
    objective: Optional[str],
    cim_schema_summary: str = "",
    datamodel: Optional[str] = None,
) -> Tuple[Optional[str], bool]:
    """
    LLM crafts ``saia_prompt`` (≤1000 chars) before ``saia_generate_spl``.

    Returns (prompt_or_none, prepared_flag).
    """
    if not getattr(settings, "tsoc_saia_llm_prepare_prompt", True):
        return None, False

    max_chars = saia_mcp_prompt_max_chars(settings)
    sys_p = load_prompt_file(_PROMPT_PREPARE)
    user = _prepare_user_message(
        search_name=search_name,
        objective=objective,
        normalized=normalized,
        datamodel=datamodel,
        cim_schema_summary=cim_schema_summary,
    )

    try:
        llm_json = await llm_json_response(
            settings,
            sys_p,
            user,
            max_tokens=min(1024, settings.litellm_analysis_max_tokens // 2),
        )
    except Exception as e:
        logger.warning("saia_prompt_prepare llm failed: %s", e)
        return None, False

    if not isinstance(llm_json, dict):
        return None, False

    raw_prompt = str(llm_json.get("saia_prompt") or "").strip()
    if not raw_prompt:
        return None, False

    prompt = _truncate_saia_prompt(raw_prompt, max_chars)
    if len(prompt) < 20:
        return None, False

    logger.info(
        "saia_prompt_prepare ok chars=%d question=%s",
        len(prompt),
        (objective or "")[:60],
    )
    return prompt, True
