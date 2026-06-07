from __future__ import annotations

from fastapi import Header, HTTPException

from correlation_config import get_settings


def require_bearer(authorization: str | None = Header(default=None)) -> None:
    settings = get_settings()
    token = (settings.correlation_bearer_token or "").strip()
    if not token:
        return
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    if authorization.removeprefix("Bearer ").strip() != token:
        raise HTTPException(status_code=401, detail="Invalid Bearer token")


def require_demo_api_key(x_demo_api_key: str | None = Header(default=None, alias="X-Demo-Api-Key")) -> None:
    settings = get_settings()
    expected = (settings.correlation_demo_api_key or "").strip()
    if not expected:
        return
    if x_demo_api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid X-Demo-Api-Key")
