"""Python version, pip bootstrap, and dependency install/verify."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import time

from setup_tool.log import LOG
from setup_tool.paths import BACKEND_DIR, REQUIRED_IMPORTS, REQUIREMENTS
from setup_tool.retry_util import step_attempts, step_delay_sec
from setup_tool.subprocess_util import run, run_maybe_live, stream_output_enabled


def step_python_version() -> bool:
    LOG.info("[PYTHON] Interpreter: %s", sys.executable)
    major, minor = sys.version_info[:2]
    if (major, minor) < (3, 11):
        LOG.error("[PYTHON] Need Python 3.11+ (have %s.%s)", major, minor)
        return False
    LOG.info("[PYTHON] OK — version %s.%s", major, minor)
    return True


def step_pip_bootstrap(*, skip_when_installer: bool = False) -> bool:
    if skip_when_installer:
        LOG.info("[PIP] Skipped (installer already installed dependencies)")
        return True
    LOG.info("[PIP] Upgrading pip, setuptools, wheel in venv")
    try:
        run_maybe_live(
            [sys.executable, "-m", "pip", "install", "-U", "pip", "setuptools", "wheel"],
            cwd=BACKEND_DIR,
        )
        ver = run([sys.executable, "-m", "pip", "--version"], cwd=BACKEND_DIR, check=False)
        LOG.info("[PIP] %s", (ver.stdout or "").strip())
        return True
    except subprocess.CalledProcessError as e:
        LOG.error("[PIP] Bootstrap failed:\n%s", e.stderr or e.stdout or e)
        return False


def verify_packages() -> bool:
    LOG.info("[DEPS] Verifying imports (%d packages)", len(REQUIRED_IMPORTS))
    ok = True
    for label, mod in REQUIRED_IMPORTS.items():
        if importlib.util.find_spec(mod) is None:
            LOG.error("[DEPS]   MISSING %s (import %s)", label, mod)
            ok = False
        else:
            LOG.info("[DEPS]   OK %s", label)
    return ok


def step_install_requirements(skip_pip: bool) -> bool:
    if skip_pip:
        LOG.info("[DEPS] Skipped (--skip-pip)")
        return verify_packages()
    if not REQUIREMENTS.is_file():
        LOG.error("[DEPS] Missing %s", REQUIREMENTS)
        return False
    LOG.info("[DEPS] Installing packages from %s", REQUIREMENTS)
    pip_cmd = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--retries",
        "10",
        "--timeout",
        "120",
        "-r",
        str(REQUIREMENTS),
    ]
    proc = None
    for attempt in range(1, step_attempts() + 1):
        if attempt > 1:
            LOG.warning("[DEPS] pip install retry (%s/%s) …", attempt, step_attempts())
            time.sleep(step_delay_sec())
        try:
            proc = run_maybe_live(pip_cmd, cwd=BACKEND_DIR, check=False)
        except subprocess.CalledProcessError:
            LOG.error("[DEPS] pip install -r requirements.txt failed (see output above)")
            continue
        if proc.returncode == 0:
            break
        if stream_output_enabled():
            LOG.error("[DEPS] pip install attempt %s failed (see output above)", attempt)
        else:
            LOG.error(
                "[DEPS] pip install attempt %s failed:\n%s",
                attempt,
                proc.stderr or proc.stdout,
            )
    if proc is None or proc.returncode != 0:
        LOG.error("[DEPS] pip install -r requirements.txt failed after %s attempts", step_attempts())
        return False
    LOG.info("[DEPS] pip install finished")
    return verify_packages()
