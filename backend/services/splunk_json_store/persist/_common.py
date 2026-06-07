"""Shared helpers for persist modules."""

from __future__ import annotations

from datetime import datetime, timezone


def stored_at_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
