"""Small URL / log-string helpers for Splunk REST."""

from __future__ import annotations

from urllib.parse import urlparse


def mgmt_netloc(base: str) -> str:
    try:
        return urlparse(base.rstrip("/")).netloc or "?"
    except Exception:
        return "?"


def truncate_log(text: str, max_len: int = 800) -> str:
    t = text or ""
    if len(t) <= max_len:
        return t
    return t[: max_len - 3] + "..."
