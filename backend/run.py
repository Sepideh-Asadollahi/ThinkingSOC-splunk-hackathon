#!/usr/bin/env python3
"""
Run the Splunk hackathon FastAPI backend (same convenience as ThinkingSOC Lite `runner_all.py`).

Usage (from anywhere):
  python /opt/thinking-soc-splunk-hackathon/backend/run.py

If `backend/.venv` (or `/opt/ThinkingSOC Lite/backend/.venv`) exists, this script re-executes
with that interpreter so you do not need to `source` the venv first.

Environment (optional):
  TSOC_HTTP_HOST  default 127.0.0.1
  TSOC_HTTP_PORT  default 9876 (also read from backend/.env if python-dotenv is installed)
  TSOC_RELOAD     set to 1 for development auto-reload

On start, any process already listening on TSOC_HTTP_PORT is stopped (SIGTERM, then SIGKILL).
Set TSOC_RUN_NO_KILL=1 to skip. Use TSOC_HTTP_PORT=9877 if you need a second instance.

When TSOC_POSTGRES_DSN is set, run.py ensures Docker Postgres is reachable first (starts
tsoc-postgres automatically if needed). Set TSOC_RUN_SKIP_POSTGRES=1 to disable that.
"""
from __future__ import annotations

import errno
import os
import re
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    env_path = BACKEND_DIR / ".env"
    if env_path.is_file():
        load_dotenv(env_path)


def _find_pids_on_port(port: int) -> list[int]:
    """PIDs listening on TCP port (Linux ss)."""
    proc = subprocess.run(
        ["ss", "-tlnp"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return []
    needle = ":{0}".format(port)
    pids: set[int] = set()
    for line in proc.stdout.splitlines():
        if needle not in line:
            continue
        for match in re.finditer(r"pid=(\d+)", line):
            pids.add(int(match.group(1)))
    return sorted(pids)


def _kill_pids(pids: list[int], *, my_pid: int) -> None:
    targets = [p for p in pids if p != my_pid and p != os.getppid()]
    if not targets:
        return
    for pid in targets:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        except PermissionError:
            sys.stderr.write("Warning: no permission to stop pid {0}\n".format(pid))
    time.sleep(0.4)
    for pid in targets:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            continue
        except PermissionError:
            continue
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    time.sleep(0.2)


def _free_port(host: str, port: int) -> None:
    """Stop prior listeners on port, then verify we can bind."""
    if os.environ.get("TSOC_RUN_NO_KILL", "").strip().lower() in ("1", "true", "yes"):
        pass
    else:
        pids = _find_pids_on_port(port)
        if pids:
            sys.stderr.write(
                "Stopping existing listener(s) on port {0}: {1}\n".format(port, ", ".join(map(str, pids)))
            )
            _kill_pids(pids, my_pid=os.getpid())

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind((host, port))
    except OSError as exc:
        if exc.errno == errno.EADDRINUSE:
            sys.stderr.write(
                "Cannot bind to {0}:{1}: address still in use.\n"
                "Try: TSOC_HTTP_PORT=9877 python3 run.py\n"
                "Or inspect: ss -tlnp | grep ':{1}'\n".format(host, port)
            )
            raise SystemExit(1) from exc
        raise
    finally:
        sock.close()


def _maybe_rerun_inside_thinking_soc_venv() -> None:
    """Prefer ThinkingSOC Lite backend venv when present (deps match root requirements.txt).

    venv interpreters are typically symlinks to the system Python; resolving symlinks
    would make the venv path indistinguishable from /usr/bin/python3 and also drop
    the launch path Python uses to discover ``pyvenv.cfg``. Compare paths as-is and
    re-exec via the symlink so the venv's site-packages are picked up.
    """
    candidates = [
        BACKEND_DIR / ".venv" / "bin" / "python3",
        BACKEND_DIR / ".venv" / "bin" / "python",
        Path("/opt/ThinkingSOC Lite/backend/.venv/bin/python3"),
        Path("/opt/ThinkingSOC Lite/backend/.venv/bin/python"),
        BACKEND_DIR.parent / ".venv" / "bin" / "python3",
        BACKEND_DIR.parent / ".venv" / "bin" / "python",
    ]
    current = Path(sys.executable)
    for venv_python in candidates:
        if not venv_python.is_file():
            continue
        if venv_python == current:
            return
        script_path = Path(__file__).resolve()
        os.execv(str(venv_python), [str(venv_python), str(script_path), *sys.argv[1:]])


def main() -> None:
    os.chdir(BACKEND_DIR)
    if str(BACKEND_DIR) not in sys.path:
        sys.path.insert(0, str(BACKEND_DIR))

    _load_dotenv()

    from config import get_settings
    from services.llm.full_trace_log import configure_trace_logging

    settings = get_settings()
    configure_trace_logging(settings)

    from devtools.dev_neo4j import ensure_dev_neo4j
    from devtools.dev_postgres import ensure_dev_postgres

    ensure_dev_postgres()
    ensure_dev_neo4j()

    import uvicorn

    host = os.environ.get("TSOC_HTTP_HOST", "127.0.0.1")
    port = int(os.environ.get("TSOC_HTTP_PORT", "9876"))
    reload = os.environ.get("TSOC_RELOAD", "").strip() in ("1", "true", "yes")

    if not reload:
        _free_port(host, port)

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=reload,
        factory=False,
    )


if __name__ == "__main__":
    _maybe_rerun_inside_thinking_soc_venv()
    main()
