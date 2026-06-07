"""Prominent completion log line — easy to spot when tailing backend logs."""

from __future__ import annotations

import logging
import os
import sys
from typing import Optional

logger = logging.getLogger(__name__)

_BANNER = "===== ANALYSIS COMPLETE ====="
_RESET = "\033[0m"
_BANNER_STYLE = "\033[1;97;42m"  # bold white on green background
_DETAIL_STYLE = "\033[1;92m"  # bold bright green


def _use_color() -> bool:
    if os.environ.get("NO_COLOR") or os.environ.get("TSOC_LOG_NO_COLOR"):
        return False
    return bool(getattr(sys.stderr, "isatty", lambda: False)())


def _colorize(message: str) -> str:
    if not _use_color():
        return message
    banner_start = message.find(_BANNER)
    if banner_start == -1:
        return f"{_DETAIL_STYLE}{message}{_RESET}"
    before = message[:banner_start]
    after_banner = message[banner_start + len(_BANNER) :]
    return (
        f"{before}{_BANNER_STYLE}{_BANNER}{_RESET}"
        f"{_DETAIL_STYLE}{after_banner}{_RESET}"
    )


def log_analysis_complete(
    *,
    pipeline: str,
    sid: Optional[str] = None,
    row_index: Optional[int] = None,
    verdict: Optional[str] = None,
    priority: Optional[str] = None,
    duration_ms: Optional[float] = None,
    extra: Optional[str] = None,
) -> None:
    parts = [_BANNER, f"pipeline={pipeline}"]
    if sid:
        parts.append(f"sid={sid}")
    if row_index is not None:
        parts.append(f"row_index={row_index}")
    if verdict:
        parts.append(f"verdict={verdict}")
    if priority:
        parts.append(f"priority={priority}")
    if duration_ms is not None:
        parts.append(f"duration_ms={duration_ms:.1f}")
    if extra:
        parts.append(extra)
    logger.info("%s", _colorize(" ".join(parts)))
