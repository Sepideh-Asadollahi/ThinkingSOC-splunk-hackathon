"""Ensure Neo4j (tsoc-neo4j) is up before the unified backend starts."""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_COMPOSE_FILE = _BACKEND_DIR / "docker-compose.yml"
NEO4J_CONTAINER = "tsoc-neo4j"


def _skip_ensure() -> bool:
    return os.environ.get("TSOC_RUN_SKIP_NEO4J", "").strip().lower() in ("1", "true", "yes")


def neo4j_container_running() -> bool:
    proc = subprocess.run(
        [
            "docker",
            "ps",
            "--filter",
            f"name=^{NEO4J_CONTAINER}$",
            "--filter",
            "status=running",
            "-q",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    return bool((proc.stdout or "").strip())


def ensure_dev_neo4j() -> None:
    if _skip_ensure():
        return
    if neo4j_container_running():
        return

    sys.stderr.write("Neo4j not running — starting tsoc-neo4j (Docker) …\n")
    if _COMPOSE_FILE.is_file():
        proc = subprocess.run(
            ["docker", "compose", "-f", str(_COMPOSE_FILE), "up", "-d", "neo4j"],
            capture_output=True,
            text=True,
            check=False,
            cwd=str(_BACKEND_DIR),
        )
        if proc.returncode != 0:
            proc = subprocess.run(
                ["docker-compose", "-f", str(_COMPOSE_FILE), "up", "-d", "neo4j"],
                capture_output=True,
                text=True,
                check=False,
                cwd=str(_BACKEND_DIR),
            )
    else:
        proc = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="")

    if proc.returncode != 0 and not neo4j_container_running():
        sys.stderr.write(
            "Could not start Neo4j. Run: cd backend && docker compose up -d neo4j\n"
            "Or skip: TSOC_RUN_SKIP_NEO4J=1 python run.py\n"
        )
        raise SystemExit(1)

    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        if neo4j_container_running():
            sys.stderr.write("Neo4j is ready.\n")
            return
        time.sleep(2)

    sys.stderr.write("Warning: Neo4j container started but health not confirmed yet.\n")
