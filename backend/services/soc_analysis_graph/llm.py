"""LiteLLM JSON stage helper for graph nodes."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from config import Settings
from services.llm.litellm_service import litellm_chat_completion
from services.soc_analysis.soc_analysis_json import (
    parse_llm_json_response,
    salvage_hunter_json_from_text,
    salvage_investigation_questions_from_text,
)

logger = logging.getLogger(__name__)


def _completion_text_for_json(out: Dict[str, Any]) -> str:
    """Prefer final answer; fall back to reasoning when the model left content empty."""
    for key in ("content", "thinking", "raw_content"):
        piece = str(out.get(key) or "").strip()
        if piece:
            return piece
    return ""


async def llm_json_response(
    settings: Settings,
    system_prompt: str,
    user_message: str,
    *,
    max_tokens: int,
    json_mode: bool = True,
    salvage_hunter: bool = False,
    salvage_investigation: bool = False,
) -> Dict[str, Any]:
    extra_body: Optional[Dict[str, Any]] = None
    if json_mode:
        extra_body = {"response_format": {"type": "json_object"}}

    try:
        out = await litellm_chat_completion(
            settings,
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=settings.litellm_analysis_temperature,
            max_tokens=max_tokens,
            extra_body=extra_body,
        )
    except Exception:
        if not json_mode:
            raise
        logger.debug("llm json_mode request failed, retrying without response_format")
        out = await litellm_chat_completion(
            settings,
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=settings.litellm_analysis_temperature,
            max_tokens=max_tokens,
        )

    pieces: List[str] = []
    for key in ("content", "thinking", "raw_content"):
        piece = str(out.get(key) or "").strip()
        if piece and piece not in pieces:
            pieces.append(piece)

    last_err: Optional[json.JSONDecodeError] = None
    for piece in pieces or [""]:
        try:
            return parse_llm_json_response(piece)
        except json.JSONDecodeError as e:
            last_err = e
            if salvage_hunter:
                recovered = salvage_hunter_json_from_text(piece)
                if recovered is not None:
                    logger.warning(
                        "llm_json hunter output recovered from non-JSON text (len=%d)",
                        len(piece),
                    )
                    return recovered
            if salvage_investigation:
                recovered = salvage_investigation_questions_from_text(piece)
                if recovered is not None:
                    logger.warning(
                        "llm_json investigation questions recovered from text (len=%d)",
                        len(piece),
                    )
                    return recovered
    if last_err is not None:
        raise last_err
    raise json.JSONDecodeError("empty LLM response", "", 0)


def per_stage_max_tokens(settings: Settings) -> int:
    return max(512, settings.litellm_analysis_max_tokens // 3)


def investigation_questions_max_tokens(settings: Settings, mt: int) -> int:
    """Reasoning models may spend the budget in chain-of-thought before JSON."""
    cap = int(settings.litellm_analysis_max_tokens or 8192)
    return min(cap, max(mt * 2, spl_review_max_tokens(settings)))


def spl_review_max_tokens(settings: Settings) -> int:
    """Enough budget for reasoning models that emit chain-of-thought before JSON."""
    return min(2048, max(1024, settings.litellm_analysis_max_tokens // 2))
