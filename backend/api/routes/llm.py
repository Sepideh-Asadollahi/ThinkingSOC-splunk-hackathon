from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from api.http_rid import http_rid

from config import Settings, get_settings
from api.deps import check_ingest_bearer
from services.llm.litellm_service import (
    LiteLLMNotConfiguredError,
    LiteLLMProviderError,
    litellm_chat_completion,
    provider_error_http_status,
)
from services.splunk_json_store import persist_llm_chat_audit_to_splunk

logger = logging.getLogger(__name__)
router = APIRouter()


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    messages: List[ChatMessage] = Field(..., min_length=1)
    model: Optional[str] = None
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, ge=1)


class ChatCompletionResponse(BaseModel):
    content: str
    model: str
    finish_reason: Optional[str] = None
    usage: Optional[Dict[str, Any]] = None


@router.get("/llm/status")
async def llm_status(settings: Settings = Depends(get_settings)) -> dict:
    """Whether explicit API key/base are set; model id from config. Never returns secret values."""
    return {
        "litellm_model": settings.litellm_model or None,
        "litellm_api_key_configured": bool(settings.litellm_api_key),
        "litellm_api_base_configured": bool(settings.litellm_api_base),
        "litellm_timeout_seconds": settings.litellm_timeout_seconds,
        "litellm_analysis_max_tokens": settings.litellm_analysis_max_tokens,
        "litellm_analysis_temperature": settings.litellm_analysis_temperature,
        "litellm_chat_default_temperature": settings.litellm_chat_default_temperature,
        "note": "If LITELLM_API_KEY is unset, LiteLLM may still use provider keys from the process environment (e.g. OPENAI_API_KEY).",
    }


@router.post(
    "/llm/chat",
    dependencies=[Depends(check_ingest_bearer)],
    response_model=ChatCompletionResponse,
)
async def llm_chat(
    request: Request,
    body: ChatCompletionRequest,
    settings: Settings = Depends(get_settings),
) -> ChatCompletionResponse:
    """Chat completion via LiteLLM (Hunter/Defender/Judge pipelines should call the service layer, not vendors)."""
    t0 = time.perf_counter()
    raw_messages = [m.model_dump() for m in body.messages]
    roles = [str(m.get("role") or "") for m in raw_messages]
    input_char_estimate = sum(len(str(m.get("content") or "")) for m in raw_messages)
    effective_temperature = body.temperature
    if effective_temperature is None and settings.litellm_chat_default_temperature is not None:
        effective_temperature = settings.litellm_chat_default_temperature
    logger.info(
        "api POST /llm/chat rid=%s model_param=%s msg_count=%d roles=%s input_chars=%d temp=%s",
        http_rid(request),
        body.model,
        len(raw_messages),
        ",".join(roles),
        input_char_estimate,
        effective_temperature,
    )
    try:
        result = await litellm_chat_completion(
            settings,
            raw_messages,
            model=body.model,
            temperature=effective_temperature,
            max_tokens=body.max_tokens,
        )
    except LiteLLMNotConfiguredError as e:
        logger.warning("api POST /llm/chat rid=%s 503 not_configured: %s", http_rid(request), e)
        raise HTTPException(status_code=503, detail=str(e)) from e
    except LiteLLMProviderError as e:
        status = provider_error_http_status(e)
        logger.warning(
            "api POST /llm/chat rid=%s %s kind=%s: %s",
            http_rid(request),
            status,
            e.kind,
            e,
        )
        raise HTTPException(status_code=status, detail=str(e)) from e
    except ValueError as e:
        logger.warning("api POST /llm/chat rid=%s 400 validation: %s", http_rid(request), e)
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("api POST /llm/chat rid=%s 500 unexpected", http_rid(request))
        raise HTTPException(status_code=500, detail="Unexpected LLM error") from e

    await persist_llm_chat_audit_to_splunk(
        settings,
        model=str(result.get("model") or ""),
        message_roles=roles,
        input_char_estimate=input_char_estimate,
        finish_reason=result.get("finish_reason") if isinstance(result.get("finish_reason"), str) else None,
        usage=result.get("usage") if isinstance(result.get("usage"), dict) else None,
    )

    logger.info(
        "api POST /llm/chat rid=%s done model=%s finish_reason=%s duration_ms=%.1f",
        http_rid(request),
        result.get("model"),
        result.get("finish_reason"),
        (time.perf_counter() - t0) * 1000.0,
    )
    return ChatCompletionResponse(
        content=result["content"],
        model=result["model"],
        finish_reason=result.get("finish_reason"),
        usage=result.get("usage"),
    )
