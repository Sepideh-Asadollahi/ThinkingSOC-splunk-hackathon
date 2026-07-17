"""LiteLLM-backed chat/completion — single integration point for LLM providers."""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from collections import deque
from typing import Any, Dict, List, Optional

from config import Settings
from services.llm.thinking_content import split_litellm_message

logger = logging.getLogger(__name__)

_RPM_WINDOW_SECONDS = 60.0
_rpm_state_guard = threading.Lock()
_rpm_timestamps: deque[float] = deque()


async def _wait_for_litellm_rpm_slot(rpm: int) -> None:
    """Apply a process-local sliding-window RPM limit without blocking the event loop."""
    wait_logged = False
    while True:
        with _rpm_state_guard:
            now = time.monotonic()
            cutoff = now - _RPM_WINDOW_SECONDS
            while _rpm_timestamps and _rpm_timestamps[0] <= cutoff:
                _rpm_timestamps.popleft()
            if len(_rpm_timestamps) < rpm:
                _rpm_timestamps.append(now)
                return
            wait_seconds = max(
                0.001,
                _rpm_timestamps[0] + _RPM_WINDOW_SECONDS - now,
            )
        if not wait_logged:
            logger.info(
                "litellm local RPM limit reached rpm=%d wait_seconds=%.2f",
                rpm,
                wait_seconds,
            )
            wait_logged = True
        await asyncio.sleep(wait_seconds)


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
        attempts: int = 1,
    ) -> None:
        super().__init__(message)
        self.kind = kind
        self.retryable = retryable
        self.attempts = attempts


def provider_error_http_status(err: LiteLLMProviderError) -> int:
    """Map provider failure kind to an HTTP status for API routes."""
    return {
        "connection": 502,
        "timeout": 504,
        "rate_limit": 503,
        "provider_busy": 503,
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
            "cannot connect to host",
            "connect call failed",
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
        if isinstance(item, litellm.exceptions.ServiceUnavailableError):
            return LiteLLMProviderError(
                "LLM provider is temporarily busy or unavailable. Automatic retries were attempted.",
                kind="provider_busy",
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
    if any(
        token in combined.lower()
        for token in (
            "resourceexhausted",
            "all workers are busy",
            "request limit reached",
            "service unavailable",
        )
    ):
        return LiteLLMProviderError(
            "LLM provider is temporarily busy or unavailable. Automatic retries were attempted.",
            kind="provider_busy",
        )

    short = str(exc).strip()
    if len(short) > 240:
        short = short[:237] + "..."
    return LiteLLMProviderError(
        "LLM provider error: {0}".format(short or type(exc).__name__),
        kind="provider_error",
    )


def _retry_delay_seconds(settings: Settings, retry_number: int) -> float:
    """Bounded exponential backoff; retry_number is one-based."""
    base = float(settings.litellm_retry_base_seconds)
    cap = float(settings.litellm_retry_max_seconds)
    return min(cap, base * (2 ** max(0, retry_number - 1)))


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

    # Avoid litellm printing "Give Feedback / Get Help" to stdout on provider errors.
    litellm.suppress_debug_info = True

    mid = (model or settings.litellm_model or "").strip()
    if not mid:
        raise LiteLLMNotConfiguredError("LITELLM_MODEL is not set")

    msgs = _normalize_messages(messages)

    kwargs: Dict[str, Any] = {
        "model": mid,
        "messages": msgs,
        "timeout": settings.litellm_timeout_seconds,
        # Keep retry ownership here so provider SDK retries cannot multiply attempts.
        "max_retries": 0,
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

    max_retries = int(settings.litellm_max_retries)
    response: Any = None
    for attempt_index in range(max_retries + 1):
        await _wait_for_litellm_rpm_slot(int(settings.litellm_rpm))
        try:
            response = await litellm.acompletion(**kwargs)
            break
        except LiteLLMNotConfiguredError:
            raise
        except ValueError:
            raise
        except Exception as e:
            mapped = _map_litellm_exception(e)
            mapped.attempts = attempt_index + 1
            retry_exhausted = attempt_index >= max_retries
            if not mapped.retryable or retry_exhausted:
                logger.warning(
                    "litellm acompletion failed model=%s messages=%d kind=%s "
                    "retryable=%s attempts=%d final=true: %s",
                    mid,
                    len(msgs),
                    mapped.kind,
                    mapped.retryable,
                    mapped.attempts,
                    mapped,
                )
                raise mapped from e

            retry_number = attempt_index + 1
            delay = _retry_delay_seconds(settings, retry_number)
            logger.warning(
                "litellm transient failure model=%s messages=%d kind=%s "
                "attempt=%d/%d retry_in_seconds=%.1f: %s",
                mid,
                len(msgs),
                mapped.kind,
                mapped.attempts,
                max_retries + 1,
                delay,
                mapped,
            )
            await asyncio.sleep(delay)

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
