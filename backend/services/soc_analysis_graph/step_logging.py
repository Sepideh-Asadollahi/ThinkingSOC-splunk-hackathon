"""Per-node timing and structured logs for the LangGraph run."""

from __future__ import annotations

import logging
import time
from typing import Any, Awaitable, Callable, Dict

from .state import SocAnalysisGraphState

logger = logging.getLogger(__name__)


async def run_graph_step(
    step: str,
    state: SocAnalysisGraphState,
    work: Callable[[], Awaitable[Dict[str, Any]]],
) -> Dict[str, Any]:
    """Log start/done (or failed) for each LangGraph node so operators can trace the pipeline."""
    sid = state.get("sid")
    logger.info("soc_graph step=%s start sid=%s", step, sid)
    t0 = time.perf_counter()
    try:
        out = await work()
    except Exception as e:
        logger.warning(
            "soc_graph step=%s failed sid=%s duration_ms=%.1f: %s",
            step,
            sid,
            (time.perf_counter() - t0) * 1000.0,
            e,
        )
        raise
    logger.info(
        "soc_graph step=%s done sid=%s duration_ms=%.1f",
        step,
        sid,
        (time.perf_counter() - t0) * 1000.0,
    )
    return out
