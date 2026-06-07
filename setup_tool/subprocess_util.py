"""Subprocess helpers."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional, Sequence

from setup_tool.log import LOG
from setup_tool.paths import REPO_ROOT

_STREAM_OUTPUT = False


def set_stream_output(enabled: bool) -> None:
    global _STREAM_OUTPUT
    _STREAM_OUTPUT = enabled


def stream_output_enabled() -> bool:
    return _STREAM_OUTPUT


def run(cmd: Sequence[str], *, cwd: Optional[Path] = None, check: bool = True) -> subprocess.CompletedProcess:
    """Run command and capture stdout/stderr (for short status checks)."""
    LOG.debug("exec: %s", " ".join(cmd))
    return subprocess.run(
        list(cmd),
        cwd=cwd or REPO_ROOT,
        check=check,
        text=True,
        capture_output=True,
    )


def run_live(cmd: Sequence[str], *, cwd: Optional[Path] = None, check: bool = True) -> subprocess.CompletedProcess:
    """Run command with stdout/stderr attached to the terminal (docker pull, pip, etc.)."""
    LOG.info("+ %s", " ".join(cmd))
    proc = subprocess.run(list(cmd), cwd=cwd or REPO_ROOT, check=False, text=True)
    if check and proc.returncode != 0:
        raise subprocess.CalledProcessError(proc.returncode, list(cmd))
    return proc


def run_maybe_live(
    cmd: Sequence[str],
    *,
    cwd: Optional[Path] = None,
    check: bool = True,
    live: bool = True,
) -> subprocess.CompletedProcess:
    if live and stream_output_enabled():
        return run_live(cmd, cwd=cwd, check=check)
    return run(cmd, cwd=cwd, check=check)
