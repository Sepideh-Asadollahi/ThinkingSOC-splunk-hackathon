"""Developer SDK exception hierarchy."""

from __future__ import annotations


class TsocSdkError(Exception):
    """Base exception for SDK failures."""


class TsocAuthError(TsocSdkError):
    """Authentication/authorization error (401/403)."""


class TsocNotFoundError(TsocSdkError):
    """Resource/path not found (404)."""


class TsocTimeoutError(TsocSdkError):
    """Request timeout from SDK transport."""


class TsocApiError(TsocSdkError):
    """HTTP/API error with structured context."""

    def __init__(self, message: str, *, status_code: int, response_text: str = "") -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text

