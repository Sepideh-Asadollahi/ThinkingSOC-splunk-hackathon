"""Reject URL query parameters that attempt to override server configuration."""

from __future__ import annotations

import logging
import re

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger(__name__)

# Legacy ingest toggles (removed from route signatures; block at the edge).
_FORBIDDEN_QUERY_EXACT = frozenset(
    {
        "auto_analyze",
        "async_mode",
    }
)

# Env-style keys must be set in backend/.env — never via query string.
_FORBIDDEN_QUERY_PREFIXES = (
    "tsoc_",
    "splunk_",
    "litellm_",
    "neo4j_",
    "qdrant_",
    "virustotal_",
)

_ENV_KEY_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")


def forbidden_config_query_keys(query_params) -> list[str]:
    """Return sorted query param names that look like config overrides."""
    blocked: list[str] = []
    for key in query_params.keys():
        normalized = key.strip().lower()
        if not normalized:
            continue
        if normalized in _FORBIDDEN_QUERY_EXACT:
            blocked.append(key)
            continue
        if any(normalized.startswith(prefix) for prefix in _FORBIDDEN_QUERY_PREFIXES):
            blocked.append(key)
            continue
        if _ENV_KEY_RE.match(key.strip()):
            blocked.append(key)
    return sorted(set(blocked))


class RejectConfigQueryParamsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        blocked = forbidden_config_query_keys(request.query_params)
        if blocked:
            logger.warning(
                "reject_config_query method=%s path=%s params=%s",
                request.method,
                request.url.path,
                ",".join(blocked),
            )
            return JSONResponse(
                status_code=400,
                content={
                    "detail": (
                        "Configuration cannot be overridden via URL query parameters. "
                        "Set backend/.env instead."
                    ),
                    "forbidden_query_params": blocked,
                },
            )
        return await call_next(request)
