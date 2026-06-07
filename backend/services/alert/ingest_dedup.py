"""In-process guard against duplicate concurrent triage for the same alert row.

Splunk fires **one HTTP POST per result row**, and the POSTs for a multi-row alert
arrive almost simultaneously. Each request runs its own FastAPI background task. If
two of them resolve to the **same** storage sid (e.g. Splunk re-sends an identical
``result``), this guard ensures only one triage runs — preventing duplicate analyses.

Scope: a single process / event loop. Claims are not shared across worker processes;
for the hackathon demo the backend runs as one process. Distinct rows (``…-1`` vs
``…-2``) claim different keys and both proceed.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Dict

logger = logging.getLogger(__name__)

# Window long enough to absorb the burst of concurrent per-row POSTs (and late
# duplicates), short enough to allow an intentional re-run afterwards.
_CLAIM_TTL_SECONDS = 120.0

_lock = asyncio.Lock()
_claims: Dict[str, float] = {}


async def claim_storage_sid(storage_sid: str, *, ttl_seconds: float = _CLAIM_TTL_SECONDS) -> bool:
    """Atomically claim ``storage_sid``. Returns False if already claimed (skip triage)."""
    key = (storage_sid or "").strip()
    if not key:
        return True
    now = time.monotonic()
    async with _lock:
        for expired in [k for k, exp in _claims.items() if exp <= now]:
            _claims.pop(expired, None)
        if key in _claims:
            return False
        _claims[key] = now + ttl_seconds
        return True


async def release_storage_sid(storage_sid: str) -> None:
    """Release a claim so a retry can run (use on failure; successes keep the TTL)."""
    key = (storage_sid or "").strip()
    if not key:
        return
    async with _lock:
        _claims.pop(key, None)


async def _reset_for_tests() -> None:
    async with _lock:
        _claims.clear()
