"""Structured application errors — clear codes and reasons instead of opaque crashes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class AppError(Exception):
    """Raised when the API should return a logical, explainable failure."""

    code: str
    message: str
    status_code: int = 500
    reason: str | None = None
    retryable: bool = False
    details: dict[str, Any] | None = None

    def __str__(self) -> str:
        if self.reason:
            return f"{self.message} ({self.reason})"
        return self.message

    @classmethod
    def bad_request(
        cls,
        message: str,
        *,
        code: str = "invalid_request",
        reason: str | None = None,
        **details: Any,
    ) -> AppError:
        return cls(
            code=code,
            message=message,
            status_code=400,
            reason=reason,
            details=details or None,
        )

    @classmethod
    def not_found(cls, message: str, *, reason: str | None = None) -> AppError:
        return cls(code="not_found", message=message, status_code=404, reason=reason)

    @classmethod
    def conflict(cls, message: str, *, reason: str | None = None) -> AppError:
        return cls(code="conflict", message=message, status_code=409, reason=reason)

    @classmethod
    def service_unavailable(
        cls,
        message: str,
        *,
        code: str = "service_unavailable",
        reason: str | None = None,
        retryable: bool = True,
    ) -> AppError:
        return cls(
            code=code,
            message=message,
            status_code=503,
            reason=reason,
            retryable=retryable,
        )

    @classmethod
    def upstream_error(
        cls,
        message: str,
        *,
        code: str = "upstream_error",
        reason: str | None = None,
        status_code: int = 502,
        retryable: bool = True,
        details: dict[str, Any] | None = None,
    ) -> AppError:
        return cls(
            code=code,
            message=message,
            status_code=status_code,
            reason=reason,
            retryable=retryable,
            details=details,
        )


def splunk_job_not_found(*, sid: str, host: str | None = None) -> AppError:
    host_hint = f" on {host}" if host else ""
    return AppError.upstream_error(
        "Splunk search job not found",
        code="splunk_job_not_found",
        reason=(
            f"No search job exists for sid={sid!r}{host_hint}. "
            "The job may have expired, the sid may be a demo/offline id, "
            "or Splunk may not have received this alert yet. "
            "Send webhook `result`/`normalized` rows for offline analysis."
        ),
        retryable=False,
        details={"sid": sid},
    )


def splunk_rest_error(exc: httpx.HTTPStatusError, *, sid: str | None = None) -> AppError:
    status = exc.response.status_code if exc.response is not None else 502
    sid_part = f" sid={sid!r}" if sid else ""
    if status == 404:
        return splunk_job_not_found(sid=sid or "unknown")
    if status in (401, 403):
        return AppError.upstream_error(
            "Splunk REST authentication failed",
            code="splunk_auth_failed",
            reason=f"Splunk returned HTTP {status}{sid_part}. Check SPLUNK_USERNAME and SPLUNK_PASSWORD.",
            retryable=False,
        )
    if status == 429:
        return AppError.upstream_error(
            "Splunk rate limit exceeded",
            code="splunk_rate_limited",
            reason=f"Splunk returned HTTP 429{sid_part}. Retry later.",
            retryable=True,
        )
    text = (exc.response.text or "")[:300] if exc.response is not None else str(exc)
    return AppError.upstream_error(
        "Splunk REST request failed",
        code="splunk_rest_error",
        reason=f"Splunk returned HTTP {status}{sid_part}: {text}".strip(),
        retryable=status >= 500,
    )


def map_exception(exc: BaseException, *, context: str | None = None) -> AppError:
    """Convert common failures into structured AppError instances."""
    if isinstance(exc, AppError):
        return exc

    from services.inventory.exceptions import InventoryConflictError, InventoryNotFoundError
    from services.llm.litellm_service import LiteLLMNotConfiguredError, LiteLLMProviderError

    prefix = f"{context}: " if context else ""

    if isinstance(exc, ValueError):
        return AppError.bad_request(str(exc), reason=f"{prefix}validation failed".strip())

    if isinstance(exc, InventoryNotFoundError):
        return AppError.not_found(str(exc), reason=f"{prefix}inventory record missing".strip())

    if isinstance(exc, InventoryConflictError):
        return AppError.conflict(str(exc), reason=f"{prefix}inventory conflict".strip())

    if isinstance(exc, LiteLLMNotConfiguredError):
        return AppError.service_unavailable(
            "LLM is not configured",
            code="llm_not_configured",
            reason=f"{prefix}set LITELLM_MODEL and API credentials in backend/.env".strip(),
            retryable=False,
        )

    if isinstance(exc, LiteLLMProviderError):
        from services.llm.litellm_service import provider_error_http_status

        return AppError.upstream_error(
            str(exc),
            code=f"llm_{exc.kind}",
            reason=f"{prefix}LLM provider call failed".strip(),
            status_code=provider_error_http_status(exc),
            retryable=exc.retryable,
        )

    if isinstance(exc, httpx.HTTPStatusError):
        return splunk_rest_error(exc)

    if isinstance(exc, httpx.TimeoutException):
        return AppError.upstream_error(
            "Upstream request timed out",
            code="upstream_timeout",
            reason=f"{prefix}{exc}".strip(),
            status_code=504,
        )

    if isinstance(exc, httpx.RequestError):
        return AppError.upstream_error(
            "Upstream service unreachable",
            code="upstream_unreachable",
            reason=f"{prefix}{exc}".strip(),
        )

    if isinstance(exc, ConnectionRefusedError):
        return AppError.service_unavailable(
            "Dependency connection refused",
            code="dependency_unavailable",
            reason=f"{prefix}{exc}. Check that Postgres, Neo4j, Splunk, or other services are running.".strip(),
        )

    if isinstance(exc, TimeoutError):
        return AppError.upstream_error(
            "Operation timed out",
            code="timeout",
            reason=f"{prefix}{exc}".strip(),
            status_code=504,
        )

    return AppError(
        code="internal_error",
        message="An unexpected error occurred",
        status_code=500,
        reason=f"{prefix}{type(exc).__name__}: {exc}".strip() if str(exc) else f"{prefix}{type(exc).__name__}".strip(),
        retryable=False,
    )
