"""Small string helpers for SOC analysis output."""

from __future__ import annotations

from typing import Any


def truncate(s: Any, max_len: int = 2000) -> str:
    t = str(s) if s is not None else ""
    if len(t) <= max_len:
        return t
    return t[: max_len - 3] + "..."
