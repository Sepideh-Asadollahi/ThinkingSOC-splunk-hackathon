"""Host prerequisite checks (before/alongside setup steps)."""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
from typing import List, Optional, Tuple

from setup_tool.log import LOG

# Hints aligned with Ubuntu apt install (docker.io + python3.12-venv)
HINT_PYTHON_VENV = (
    "Install Python venv support:\n"
    "  sudo apt-get update\n"
    "  sudo apt-get install -y python3.12-venv python3-pip\n"
    "  # or: sudo apt-get install -y python3-venv python3-pip"
)

HINT_DOCKER_INSTALL = (
    "Install Docker (Ubuntu — docker.io package):\n"
    "  sudo apt-get update\n"
    "  sudo apt-get install -y ca-certificates curl\n"
    "  sudo install -m 0755 -d /etc/apt/keyrings\n"
    "  sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc\n"
    "  sudo chmod a+r /etc/apt/keyrings/docker.asc\n"
    "  echo \"deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] "
    "https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable\" | "
    "sudo tee /etc/apt/sources.list.d/docker.list > /dev/null\n"
    "  sudo apt-get update\n"
    "  sudo apt-get install -y docker.io\n"
    "  # compose (pick one):\n"
    "  sudo apt-get install -y docker-compose\n"
    "  # or: sudo apt-get install -y docker-compose-plugin"
)

HINT_DOCKER_DAEMON = (
    "Docker is installed but the daemon is not reachable. Try:\n"
    "  sudo systemctl start docker\n"
    "  sudo systemctl enable docker\n"
    "  # add your user to the docker group (then re-login):\n"
    "  sudo usermod -aG docker $USER"
)


def find_compose_cmd() -> Optional[List[str]]:
    """Return docker compose v2 plugin or legacy docker-compose v1."""
    if shutil.which("docker"):
        proc = subprocess.run(
            ["docker", "compose", "version"],
            capture_output=True,
            text=True,
        )
        if proc.returncode == 0:
            return ["docker", "compose"]
    if shutil.which("docker-compose"):
        return ["docker-compose"]
    return None


def _docker_client_works() -> Tuple[bool, str]:
    if not shutil.which("docker"):
        return False, "docker command not found in PATH"
    proc = subprocess.run(
        ["docker", "info"],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        return False, err or "docker info failed"
    return True, ""


def check_host_python() -> bool:
    """Launcher interpreter: version + stdlib venv (needed before backend/.venv)."""
    LOG.info("[PREREQ] Host Python: %s", sys.executable)
    major, minor = sys.version_info[:2]
    if (major, minor) < (3, 11):
        LOG.error("[PREREQ] Need Python 3.11+ on the host (have %s.%s)", major, minor)
        return False
    LOG.info("[PREREQ]   OK Python %s.%s", major, minor)

    if importlib.util.find_spec("venv") is None:
        LOG.error("[PREREQ]   MISSING python venv module")
        LOG.error("%s", HINT_PYTHON_VENV)
        return False
    LOG.info("[PREREQ]   OK python venv module")

    # Optional: system pip (setup uses venv pip after re-exec; this is advisory)
    if importlib.util.find_spec("pip") is None:
        LOG.warning(
            "[PREREQ]   WARN system pip not found (OK if you only use backend/.venv after setup)"
        )
        LOG.warning("  Install if needed: sudo apt-get install -y python3-pip")
    else:
        LOG.info("[PREREQ]   OK system pip module")
    return True


def check_docker(skip_docker: bool) -> bool:
    if skip_docker:
        LOG.info("[PREREQ] Docker checks skipped (--skip-docker)")
        return True

    LOG.info("[PREREQ] Checking Docker …")
    if not shutil.which("docker"):
        LOG.error("[PREREQ]   MISSING docker")
        LOG.error("%s", HINT_DOCKER_INSTALL)
        return False
    ver = subprocess.run(["docker", "--version"], capture_output=True, text=True, check=False)
    LOG.info("[PREREQ]   OK %s", (ver.stdout or ver.stderr or "").strip())

    compose = find_compose_cmd()
    if not compose:
        LOG.error("[PREREQ]   MISSING docker compose (need docker-compose or docker compose plugin)")
        LOG.error("%s", HINT_DOCKER_INSTALL)
        return False
    cver = subprocess.run([*compose, "version"], capture_output=True, text=True, check=False)
    LOG.info("[PREREQ]   OK compose: %s", (cver.stdout or cver.stderr or "").strip().split("\n")[0])

    ok, err = _docker_client_works()
    if not ok:
        LOG.error("[PREREQ]   Docker daemon not reachable: %s", err.split("\n")[0] if err else "unknown")
        LOG.error("%s", HINT_DOCKER_DAEMON)
        return False
    LOG.info("[PREREQ]   OK Docker daemon")
    return True


def step_prerequisites(skip_docker: bool) -> bool:
    ok = check_host_python()
    ok = check_docker(skip_docker) and ok
    if ok:
        LOG.info("[PREREQ] OK")
    return ok
