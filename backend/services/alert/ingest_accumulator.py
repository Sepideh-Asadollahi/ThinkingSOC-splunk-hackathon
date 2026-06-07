"""Buffer per-row webhook POSTs for one Splunk job, then analyze all rows together.

Splunk fires **one HTTP POST per result row** (same ``sid``, different ``result``).
Instead of guessing the row index from a single POST, this accumulator collects every
POST for a ``sid`` in a short debounce window, dedupes by result fingerprint, and once
no new POST arrives for the window it hands the **full ordered row set** to a flush
callback. The number of rows is derived from the buffered content + sid — exactly what
"how many rows does this alert have" needs.

Scope: a single process / event loop (FastAPI on one uvicorn worker). Buffers are
in-memory; a restart drops any half-collected job.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional

from config import Settings
from models.handoff import SplunkAlertIngest
from services.alert.ingest_request_trace import fingerprint_result_row
from services.soc_analysis.analysis_audit import splunk_job_sid

logger = logging.getLogger(__name__)

# Callback signature: (settings, base_sid, rows, template_handoff) -> awaitable
FlushCallback = Callable[[Settings, str, List[Dict[str, Any]], SplunkAlertIngest], Awaitable[None]]


@dataclass
class _SidBucket:
    search_name: Optional[str]
    normalized: Dict[str, Any]
    orig_sid: Optional[str]
    rows: List[Dict[str, Any]] = field(default_factory=list)
    fingerprints: set[str] = field(default_factory=set)
    generation: int = 0
    last_update: float = 0.0
    flush_task: Optional[asyncio.Task] = None


_lock = asyncio.Lock()
_buckets: Dict[str, _SidBucket] = {}


def _rows_from_handoff(handoff: SplunkAlertIngest) -> List[Dict[str, Any]]:
    return [r for r in handoff.results if isinstance(r, dict)]


async def accumulate_ingest_row(
    settings: Settings,
    handoff: SplunkAlertIngest,
    *,
    debounce_seconds: float,
    flush_callback: FlushCallback,
) -> Dict[str, Any]:
    """Buffer this POST's row(s) under the job (base) sid and (re)arm the debounce flush."""
    base_sid = splunk_job_sid(handoff.sid) or (handoff.sid or "")
    incoming = _rows_from_handoff(handoff)
    now = time.monotonic()

    async with _lock:
        bucket = _buckets.get(base_sid)
        if bucket is None:
            bucket = _SidBucket(
                search_name=handoff.search_name,
                normalized=dict(handoff.normalized or {}),
                orig_sid=handoff.orig_sid,
            )
            _buckets[base_sid] = bucket

        added = 0
        duplicates = 0
        for row in incoming:
            fp = fingerprint_result_row(row)
            if fp in bucket.fingerprints:
                duplicates += 1
                continue
            bucket.fingerprints.add(fp)
            bucket.rows.append(row)
            added += 1

        bucket.last_update = now
        bucket.generation += 1
        my_gen = bucket.generation
        if bucket.flush_task is not None and not bucket.flush_task.done():
            bucket.flush_task.cancel()
        bucket.flush_task = asyncio.create_task(
            _flush_after(base_sid, my_gen, debounce_seconds, settings, flush_callback)
        )
        buffered = len(bucket.rows)

    logger.info(
        "ingest_buffer accumulate base_sid=%s added=%d duplicates=%d buffered_rows=%d "
        "debounce_s=%.1f search_name=%s",
        base_sid,
        added,
        duplicates,
        buffered,
        debounce_seconds,
        handoff.search_name,
    )
    return {
        "base_sid": base_sid,
        "buffered_rows": buffered,
        "added": added,
        "duplicates": duplicates,
    }


async def _flush_after(
    base_sid: str,
    my_gen: int,
    debounce_seconds: float,
    settings: Settings,
    flush_callback: FlushCallback,
) -> None:
    try:
        await asyncio.sleep(debounce_seconds)
    except asyncio.CancelledError:
        return

    async with _lock:
        bucket = _buckets.get(base_sid)
        if bucket is None or bucket.generation != my_gen:
            # A newer POST re-armed the flush; this stale task does nothing.
            return
        _buckets.pop(base_sid, None)
        rows = list(bucket.rows)
        template = SplunkAlertIngest(
            sid=base_sid,
            orig_sid=bucket.orig_sid,
            search_name=bucket.search_name,
            normalized=dict(bucket.normalized or {}),
            results=rows,
        )

    if not rows:
        return

    logger.info(
        "ingest_buffer flush base_sid=%s total_rows=%d search_name=%s",
        base_sid,
        len(rows),
        template.search_name,
    )
    try:
        await flush_callback(settings, base_sid, rows, template)
    except Exception:
        logger.warning("ingest_buffer flush failed base_sid=%s", base_sid, exc_info=True)


async def _reset_for_tests() -> None:
    async with _lock:
        for bucket in _buckets.values():
            if bucket.flush_task is not None and not bucket.flush_task.done():
                bucket.flush_task.cancel()
        _buckets.clear()
