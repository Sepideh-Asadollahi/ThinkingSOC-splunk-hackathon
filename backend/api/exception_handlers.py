"""FastAPI exception handlers — structured errors instead of opaque 500 crashes."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from api.app_errors import AppError, map_exception
from api.http_rid import http_rid

logger = logging.getLogger(__name__)

_STATUS_DEFAULT_CODES = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    409: "conflict",
    422: "validation_error",
    429: "rate_limited",
    502: "bad_gateway",
    503: "service_unavailable",
    504: "gateway_timeout",
}


def build_error_body(
    *,
    code: str,
    message: str,
    request_id: str,
    reason: str | None = None,
    retryable: bool = False,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """JSON body compatible with FastAPI clients (`detail`) and structured UIs (`error`)."""
    body: dict[str, Any] = {
        "detail": message,
        "error": {
            "code": code,
            "message": message,
            "retryable": retryable,
        },
        "request_id": request_id,
    }
    if reason:
        body["error"]["reason"] = reason
    if details:
        body["error"]["details"] = details
    return body


def _detail_to_message(detail: Any) -> str:
    if detail is None:
        return "Request failed"
    if isinstance(detail, str):
        return detail
    if isinstance(detail, dict):
        if detail.get("message"):
            return str(detail["message"])
        if detail.get("error"):
            return str(detail["error"])
        return str(detail)
    if isinstance(detail, list):
        return "Validation failed"
    return str(detail)


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    rid = http_rid(request)
    logger.warning(
        "app_error rid=%s code=%s status=%s message=%s reason=%s",
        rid,
        exc.code,
        exc.status_code,
        exc.message,
        exc.reason,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=build_error_body(
            code=exc.code,
            message=exc.message,
            reason=exc.reason,
            retryable=exc.retryable,
            details=exc.details,
            request_id=rid,
        ),
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    rid = http_rid(request)
    code = _STATUS_DEFAULT_CODES.get(exc.status_code, "http_error")
    message = _detail_to_message(exc.detail)
    reason = None
    details = None
    if isinstance(exc.detail, dict):
        reason = exc.detail.get("reason")
        if isinstance(exc.detail.get("details"), dict):
            details = exc.detail["details"]
        if exc.detail.get("code"):
            code = str(exc.detail["code"])
    return JSONResponse(
        status_code=exc.status_code,
        content=build_error_body(
            code=code,
            message=message,
            reason=reason,
            details=details,
            request_id=rid,
        ),
    )


def _format_validation_errors(exc: RequestValidationError) -> tuple[str, list[dict[str, Any]]]:
    items: list[dict[str, Any]] = []
    for err in exc.errors():
        loc = err.get("loc") or ()
        field = ".".join(str(part) for part in loc if part != "body")
        items.append(
            {
                "field": field or "body",
                "message": str(err.get("msg") or "invalid value"),
                "type": str(err.get("type") or "value_error"),
            }
        )
    if not items:
        return "Request validation failed", items
    first = items[0]
    summary = f"Invalid field '{first['field']}': {first['message']}"
    if len(items) > 1:
        summary += f" (+{len(items) - 1} more)"
    return summary, items


async def request_validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    rid = http_rid(request)
    message, items = _format_validation_errors(exc)
    logger.info("validation_error rid=%s path=%s errors=%d", rid, request.url.path, len(items))
    return JSONResponse(
        status_code=422,
        content=build_error_body(
            code="validation_error",
            message=message,
            reason="Fix the request body or query parameters and retry.",
            details={"fields": items},
            request_id=rid,
        ),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    rid = http_rid(request)
    mapped = map_exception(exc, context=f"{request.method} {request.url.path}")
    if mapped.status_code >= 500:
        logger.exception(
            "unhandled_exception rid=%s path=%s mapped_code=%s",
            rid,
            request.url.path,
            mapped.code,
        )
    else:
        logger.warning(
            "handled_exception rid=%s path=%s code=%s message=%s",
            rid,
            request.url.path,
            mapped.code,
            mapped.message,
        )
    return JSONResponse(
        status_code=mapped.status_code,
        content=build_error_body(
            code=mapped.code,
            message=mapped.message,
            reason=mapped.reason,
            retryable=mapped.retryable,
            details=mapped.details,
            request_id=rid,
        ),
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, request_validation_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
