"""HTTP request id for correlating route logs with ``RequestLoggingMiddleware``."""

from __future__ import annotations

from fastapi import Request


def http_rid(request: Request) -> str:
    return getattr(request.state, "request_id", None) or "-"
