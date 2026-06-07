"""Virtual environment creation and re-exec."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

from setup_tool.log import LOG
from setup_tool.paths import REQUIREMENTS, SETUP_SCRIPT, VENV_DIR


def venv_python() -> Path:
    if sys.platform == "win32":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def in_project_venv() -> bool:
    """True when running inside backend/.venv (sys.prefix; Debian may symlink python to /usr/bin)."""
    try:
        return Path(sys.prefix).resolve() == VENV_DIR.resolve()
    except OSError:
        return False


def ensure_running_in_venv() -> None:
    """Create backend/.venv if needed, then re-exec setup.py inside it."""
    if in_project_venv():
        LOG.info("[VENV] Using %s", sys.executable)
        return

    if not REQUIREMENTS.is_file():
        LOG.error("[VENV] Cannot continue — missing %s", REQUIREMENTS)
        raise SystemExit(1)

    if importlib.util.find_spec("venv") is None:
        from setup_tool.prerequisites import HINT_PYTHON_VENV

        LOG.error("[VENV] Python venv module missing")
        LOG.error("%s", HINT_PYTHON_VENV)
        raise SystemExit(1)

    py = venv_python()
    if not VENV_DIR.is_dir():
        LOG.info("[VENV] Creating virtual environment at %s", VENV_DIR)
        proc = subprocess.run(
            [sys.executable, "-m", "venv", str(VENV_DIR)],
            cwd=SETUP_SCRIPT.parent,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            LOG.error("[VENV] venv creation failed:\n%s", proc.stderr or proc.stdout)
            raise SystemExit(1)
        LOG.info("[VENV] Created %s", VENV_DIR)
    else:
        LOG.info("[VENV] Found existing %s", VENV_DIR)

    if not py.is_file():
        LOG.error("[VENV] Interpreter not found at %s", py)
        raise SystemExit(1)

    LOG.info("[VENV] Re-launching setup with %s", py)
    os.environ["TSOC_SETUP_PREREQ_OK"] = "1"
    os.execv(str(py), [str(py), str(SETUP_SCRIPT.resolve()), *sys.argv[1:]])
