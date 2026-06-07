"""Log each HTTP request with duration and a stable request id for troubleshooting."""

from __future__ import annotations

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

# High-churn browser traffic; still get X-Request-ID but avoid log noise.
_QUIET_PATHS = frozenset({"/docs", "/redoc", "/openapi.json", "/favicon.ico"})


def _should_skip_request_log(path: str) -> bool:
    return path in _QUIET_PATHS


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        if path == "/health":
            return await call_next(request)

        rid = (request.headers.get("x-request-id") or "").strip() or str(uuid.uuid4())
        request.state.request_id = rid
        t0 = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            logger.exception(
                "http_request rid=%s method=%s path=%s failed_after_ms=%.1f",
                rid,
                request.method,
                path,
                elapsed_ms,
            )
            raise

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        if not _should_skip_request_log(path):
            logger.info(
                "http_request rid=%s method=%s path=%s status=%s duration_ms=%.1f",
                rid,
                request.method,
                path,
                response.status_code,
                elapsed_ms,
            )
        response.headers["X-Request-ID"] = rid
        return response
