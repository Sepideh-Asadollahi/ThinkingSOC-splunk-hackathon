"""SOC analysis — Defender / Hunter / Judge assembly, fallback, and runner."""

from __future__ import annotations

from typing import Any

from .append_log import append_analysis_log

__all__ = [
    "append_analysis_log",
    "run_analysis",
]


def __getattr__(name: str) -> Any:
    if name == "run_analysis":
        from .runner import run_analysis

        return run_analysis
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
