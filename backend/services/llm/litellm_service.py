"""LiteLLM-backed chat/completion — single integration point for LLM providers."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from config import Settings
from services.llm.thinking_content import split_litellm_message

logger = logging.getLogger(__name__)


def _cap_max_tokens(settings: Settings, max_tokens: Optional[int]) -> Optional[int]:
    cap = int(settings.litellm_max_tokens)
    if max_tokens is None:
        return cap
    return min(int(max_tokens), cap)


class LiteLLMNotConfiguredError(ValueError):
    """Raised when no model id is configured."""


class LiteLLMProviderError(RuntimeError):
    """LLM provider call failed (network, auth, rate limit, etc.)."""

    def __init__(
        self,
        message: str,
        *,
        kind: str = "provider_error",
        retryable: bool = True,
    ) -> None:
        super().__init__(message)
        self.kind = kind
        self.retryable = retryable


def provider_error_http_status(err: LiteLLMProviderError) -> int:
    """Map provider failure kind to an HTTP status for API routes."""
    return {
        "connection": 502,
        "timeout": 504,
        "rate_limit": 503,
        "auth": 503,
        "bad_request": 400,
        "context_window": 400,
    }.get(err.kind, 502)


def _connection_indicators(text: str) -> bool:
    lower = text.lower()
    return any(
        token in lower
        for token in (
            "connection error",
            "server disconnected",
            "connection refused",
            "connection reset",
            "failed to connect",
            "network is unreachable",
            "name or service not known",
        )
    )


def _map_litellm_exception(exc: Exception) -> LiteLLMProviderError:
    """Turn LiteLLM/vendor exceptions into stable, user-facing errors."""
    import litellm

    chain: list[Exception] = []
    current: Optional[BaseException] = exc
    while isinstance(current, Exception) and current not in chain:
        chain.append(current)
        current = current.__cause__  # type: ignore[assignment]

    for item in chain:
        if isinstance(item, litellm.exceptions.APIConnectionError):
            return LiteLLMProviderError(
                "LLM provider is unreachable (connection failed). Check LITELLM_API_BASE "
                "and that the provider is running, then retry.",
                kind="connection",
            )
        if isinstance(item, litellm.exceptions.Timeout):
            return LiteLLMProviderError(
                "LLM request timed out. The provider took too long to respond; retry with a shorter prompt.",
                kind="timeout",
            )
        if isinstance(item, litellm.exceptions.RateLimitError):
            return LiteLLMProviderError(
                "LLM provider rate limit exceeded. Wait briefly and retry.",
                kind="rate_limit",
            )
        if isinstance(item, litellm.exceptions.AuthenticationError):
            return LiteLLMProviderError(
                "LLM provider rejected the API key. Verify LITELLM_API_KEY and provider credentials.",
                kind="auth",
                retryable=False,
            )
        if isinstance(item, litellm.exceptions.ContextWindowExceededError):
            return LiteLLMProviderError(
                "Prompt exceeds the model context window. Shorten the input and retry.",
                kind="context_window",
                retryable=False,
            )
        if isinstance(item, (litellm.exceptions.BadRequestError, litellm.exceptions.InvalidRequestError)):
            return LiteLLMProviderError(
                "LLM provider rejected the request. Check model id and request parameters.",
                kind="bad_request",
                retryable=False,
            )

    combined = " ".join(str(item) for item in chain).strip()
    if _connection_indicators(combined):
        return LiteLLMProviderError(
            "LLM provider disconnected during the request. The upstream service may be overloaded "
            "or restarting; retry in a moment.",
            kind="connection",
        )
    if "timeout" in combined.lower():
        return LiteLLMProviderError(
            "LLM request timed out. The provider took too long to respond; retry with a shorter prompt.",
            kind="timeout",
        )

    short = str(exc).strip()
    if len(short) > 240:
        short = short[:237] + "..."
    return LiteLLMProviderError(
        "LLM provider error: {0}".format(short or type(exc).__name__),
        kind="provider_error",
    )


def _normalize_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for m in messages:
        role = m.get("role")
        content = m.get("content")
        if role not in ("system", "user", "assistant"):
            raise ValueError("each message must have role system|user|assistant and content")
        if content is None or (isinstance(content, str) and not str(content).strip() and role != "assistant"):
            raise ValueError("message content is required")
        out.append({"role": role, "content": content})
    return out


async def litellm_chat_completion(
    settings: Settings,
    messages: List[Dict[str, Any]],
    *,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    extra_body: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Run a chat completion via LiteLLM (`acompletion`).

    API keys: set `LITELLM_API_KEY` or rely on provider env vars
    (e.g. `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`) as supported by LiteLLM.
    """
    # Lazy import so tests can patch `litellm.acompletion` without importing litellm at collection time.
    import litellm

    mid = (model or settings.litellm_model or "").strip()
    if not mid:
        raise LiteLLMNotConfiguredError("LITELLM_MODEL is not set")

    msgs = _normalize_messages(messages)

    kwargs: Dict[str, Any] = {
        "model": mid,
        "messages": msgs,
        "timeout": settings.litellm_timeout_seconds,
    }
    if settings.litellm_api_key:
        kwargs["api_key"] = settings.litellm_api_key
    if settings.litellm_api_base:
        kwargs["api_base"] = settings.litellm_api_base
    if temperature is not None:
        kwargs["temperature"] = temperature
    capped = _cap_max_tokens(settings, max_tokens)
    if capped is not None:
        kwargs["max_tokens"] = capped
    if extra_body:
        kwargs["extra_body"] = extra_body

    try:
        response = await litellm.acompletion(**kwargs)
    except LiteLLMNotConfiguredError:
        raise
    except ValueError:
        raise
    except Exception as e:
        mapped = _map_litellm_exception(e)
        logger.warning(
            "litellm acompletion failed model=%s messages=%d kind=%s retryable=%s: %s",
            mid,
            len(msgs),
            mapped.kind,
            mapped.retryable,
            mapped,
        )
        raise mapped from e

    choice = response.choices[0]
    message = choice.message
    raw_content = getattr(message, "content", None) or ""
    thinking, content = split_litellm_message(message)

    usage: Optional[Dict[str, Any]] = None
    if getattr(response, "usage", None) is not None:
        u = response.usage
        usage = {
            "prompt_tokens": getattr(u, "prompt_tokens", None),
            "completion_tokens": getattr(u, "completion_tokens", None),
            "total_tokens": getattr(u, "total_tokens", None),
        }

    finish_reason = getattr(choice, "finish_reason", None)
    logger.info(
        "litellm completion model=%s finish_reason=%s usage=%s answer_chars=%d thinking_chars=%s",
        getattr(response, "model", mid) or mid,
        finish_reason,
        usage,
        len(content or ""),
        len(thinking) if thinking else 0,
    )
    if thinking:
        logger.info(
            "litellm thinking model=%s finish_reason=%s\n%s",
            getattr(response, "model", mid) or mid,
            finish_reason,
            thinking,
        )
    if content:
        logger.info(
            "litellm answer model=%s finish_reason=%s\n%s",
            getattr(response, "model", mid) or mid,
            finish_reason,
            content,
        )

    return {
        "content": content,
        "thinking": thinking,
        "raw_content": raw_content,
        "model": getattr(response, "model", mid) or mid,
        "finish_reason": finish_reason,
        "usage": usage,
    }
