"""Shared retry helpers for setup steps (network flakes)."""

from __future__ import annotations

import asyncio
import os
import time
from typing import Awaitable, Callable, TypeVar

T = TypeVar("T")


def step_attempts() -> int:
    return max(1, int(os.environ.get("TSOC_STEP_AUTO_ATTEMPTS", "3")))


def step_delay_sec() -> int:
    return max(1, int(os.environ.get("TSOC_STEP_RETRY_DELAY", "5")))


def retry_sync(label: str, fn: Callable[[], T]) -> T:
    """Run fn with automatic retries; raise last exception if all fail."""
    attempts = step_attempts()
    delay = step_delay_sec()
    last: BaseException | None = None
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except BaseException as exc:
            last = exc
            if attempt < attempts:
                time.sleep(delay)
    assert last is not None
    raise last


async def retry_async(label: str, fn: Callable[[], Awaitable[T]]) -> T:
    attempts = step_attempts()
    delay = step_delay_sec()
    last: BaseException | None = None
    for attempt in range(1, attempts + 1):
        try:
            return await fn()
        except BaseException as exc:
            last = exc
            if attempt < attempts:
                await asyncio.sleep(delay)
    assert last is not None
    raise last
