"""Shared FastAPI dependencies."""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from typing import Optional

from fastapi import Depends, Header, HTTPException, Request

from config import Settings, get_settings

_RATE_LIMIT_BUCKETS: dict[str, deque[float]] = defaultdict(deque)
_RATE_LIMIT_LOCK = threading.Lock()


def _extract_bearer_token(authorization: Optional[str]) -> Optional[str]:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    return authorization[7:].strip()


def check_ingest_bearer(
    authorization: Optional[str] = Header(None),
    settings: Settings = Depends(get_settings),
) -> None:
    expected = settings.tsoc_ingest_token
    if not expected:
        return
    token = _extract_bearer_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing Authorization bearer token")
    if token != expected:
        raise HTTPException(status_code=403, detail="Invalid bearer token")


def check_admin_bearer(
    authorization: Optional[str] = Header(None),
    settings: Settings = Depends(get_settings),
) -> None:
    # Backward-compatible fallback keeps existing deploys working.
    expected = settings.tsoc_admin_token or settings.tsoc_ingest_token
    if not expected:
        return
    token = _extract_bearer_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing Authorization bearer token")
    if token != expected:
        raise HTTPException(status_code=403, detail="Invalid bearer token")


def rate_limit_sensitive(
    request: Request,
    authorization: Optional[str] = Header(None),
    settings: Settings = Depends(get_settings),
) -> None:
    if not settings.tsoc_rate_limit_enabled:
        return

    token = _extract_bearer_token(authorization)
    forwarded_for = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
    client_ip = forwarded_for or (request.client.host if request.client else "unknown")
    identity = token or client_ip or "unknown"
    key = "{0}:{1}".format(request.url.path, identity)

    now = time.time()
    window = max(1, int(settings.tsoc_rate_limit_window_seconds))
    max_requests = max(1, int(settings.tsoc_rate_limit_max_requests))
    cutoff = now - float(window)

    with _RATE_LIMIT_LOCK:
        bucket = _RATE_LIMIT_BUCKETS[key]
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= max_requests:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        bucket.append(now)


def reset_rate_limit_buckets() -> None:
    with _RATE_LIMIT_LOCK:
        _RATE_LIMIT_BUCKETS.clear()
